"""Регистрация, вход и данные текущего пользователя."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.schemas import LoginRequest, Token, UserCreate, UserOut
from app.security import (
    CurrentUser,
    DBSession,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=UserOut, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: DBSession) -> User:
    """Создать аккаунт. Пароль сохраняется только как Argon2-хеш.

    После регистрации можно сразу входить — подтверждение email не требуется.
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
        db.commit()
    except IntegrityError:
        # Гонка двух параллельных регистраций — уникальный индекс спасает
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Имя пользователя или email уже заняты",
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DBSession) -> Token:
    """Войти по email и паролю и получить JWT.

    Сообщение об ошибке одинаковое для «email не найден» и «пароль неверный» —
    не раскрываем, какие email зарегистрированы.
    """
    email = str(payload.email).lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return Token(access_token=create_access_token(user.id))


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