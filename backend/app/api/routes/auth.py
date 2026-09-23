"""Регистрация, вход, подтверждение email и данные пользователя."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import EmailVerificationToken, User
from app.schemas import (
    LoginRequest,
    RegisterResponse,
    ResendRequest,
    ResendResponse,
    Token,
    UserCreate,
    UserOut,
)
from app.security import (
    CurrentUser,
    DBSession,
    create_access_token,
    generate_verification_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.email_service import EmailSendError, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])

# Cooldown повторной отправки письма (анти-спам, серверный)
RESEND_COOLDOWN_SECONDS = 60

VERIFY_INVALID = "Недействительная ссылка подтверждения."
VERIFY_USED = "Email уже был подтверждён."
VERIFY_EXPIRED = "Срок действия ссылки подтверждения истёк. Запросите новое письмо."


def _create_verification_token(db, user: User) -> str:
    """Создать запись токена подтверждения. Вернёт сырой токен (для письма).

    В БД попадает только SHA-256-хеш; сырой токен существует в памяти
    и уходит в письмо.
    """
    raw_token = generate_verification_token()
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.email_verification_token_expire_minutes),
        )
    )
    return raw_token


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: DBSession) -> RegisterResponse:
    """Создать аккаунт и отправить письмо с подтверждением email.

    Пользователь НЕ логинится автоматически: сначала нужно перейти по ссылке
    из письма (email_verified=False -> 403 при попытке входа).

    Если Resend не смог отправить письмо — аккаунт и токен остаются созданы,
    а клиенту предлагается «Отправить письмо повторно» (не удаляем аккаунт:
    так пользователь не теряет username/email и может запросить письмо заново).
    """
    username = payload.username.strip()
    email = str(payload.email).lower().strip()

    existing = db.scalar(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing is not None:
        if existing.email == email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Этот email уже зарегистрирован",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Это имя пользователя уже занято",
        )

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()  # получаем user.id для FK токена ещё до commit
    except IntegrityError:
        # Гонка двух параллельных регистраций — уникальный индекс спасает
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Имя пользователя или email уже заняты",
        ) from None

    raw_token = _create_verification_token(db, user)
    db.commit()

    try:
        verification_url = send_verification_email(
            email=email, username=username, verification_token=raw_token
        )
    except EmailSendError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Аккаунт создан, но письмо отправить не удалось. "
                "Через минуту нажмите «Отправить письмо повторно». "
                f"Причина: {exc}"
            ),
        ) from exc

    # Ссылка в ответе — только когда письма реально не отправляются
    # (dev-режим или почта не настроена). В production она не возвращается.
    expose_link = settings.email_dev_mode or not settings.resend_api_key.strip()
    return RegisterResponse(
        message=(
            "Регистрация успешна. Проверь почту — мы отправили письмо для подтверждения."
            if not expose_link
            else "Регистрация успешна. (dev) Письмо не отправляется — подтверди email по ссылке ниже."
        ),
        email=email,
        verification_url=verification_url if expose_link else None,
    )


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DBSession) -> Token:
    """Войти по email и паролю и получить JWT.

    Два разных отказа: 401 (неверные данные) и 403 (email не подтверждён).
    Про существование email отдельного сообщения нет — не раскрываем.
    """
    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Сначала подтвердите email — мы отправили письмо с ссылкой.",
        )

    return Token(access_token=create_access_token(user.id))


@router.get("/verify-email")
def verify_email(
    db: DBSession,
    token: str = Query(min_length=10, max_length=200),
) -> dict:
    """Подтвердить email по одноразовому токену из письма.

    Состояния: 200 — успех; 400 — токен не найден; 409 — уже использован;
    410 — истёк срок действия.
    """
    now = datetime.now(timezone.utc)
    record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_token(token)
        )
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=VERIFY_INVALID)

    if record.used_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=VERIFY_USED)

    if record.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=VERIFY_EXPIRED)

    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=VERIFY_INVALID)

    user.email_verified = True
    record.used_at = now  # токен одноразовый: повторно уже не сработает
    db.commit()
    return {
        "message": "Email успешно подтверждён. Теперь можно войти.",
        "email": user.email,
    }


@router.post("/resend-verification", response_model=ResendResponse)
def resend_verification(payload: ResendRequest, db: DBSession) -> ResendResponse:
    """Повторно отправить письмо подтверждения (cooldown 60 сек).

    Старые активные токены инвалидируются — действительна только новая ссылка.
    """
    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # Не раскрываем, существует ли аккаунт с таким email
        return ResendResponse(
            message="Если аккаунт существует и email не подтверждён — мы отправили письмо."
        )
    if user.email_verified:
        return ResendResponse(message="Email уже подтверждён — можно входить.")

    now = datetime.now(timezone.utc)
    last_created = db.scalar(
        select(EmailVerificationToken.created_at)
        .where(EmailVerificationToken.user_id == user.id)
        .order_by(EmailVerificationToken.created_at.desc())
        .limit(1)
    )
    if last_created is not None:
        elapsed = (now - last_created).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Письмо уже отправляли недавно. Повторите через {wait} сек.",
            )

    # Инвалидируем все прежние активные токены пользователя
    for old in db.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
    ):
        old.used_at = now

    raw_token = _create_verification_token(db, user)
    db.commit()

    try:
        verification_url = send_verification_email(
            email=email, username=user.username, verification_token=raw_token
        )
    except EmailSendError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось отправить письмо. {exc}",
        ) from exc

    expose_link = settings.email_dev_mode or not settings.resend_api_key.strip()
    return ResendResponse(
        message=(
            "Новое письмо отправлено. Проверь почту."
            if not expose_link
            else "(dev) Письмо не отправляется — подтверди email по ссылке ниже."
        ),
        verification_url=verification_url if expose_link else None,
    )


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(current_user: CurrentUser, db: DBSession) -> None:
    """Удалить свой аккаунт.

    Требуется JWT: удаляется только пользователь из токена, чужой аккаунт
    удалить невозможно. Вместе с пользователем каскадно удаляются история
    просмотров и токены подтверждения email (FK ON DELETE CASCADE).
    """
    db.delete(current_user)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> User:
    """Данные текущего пользователя (требует Bearer-токен)."""
    return current_user