"""Безопасность: пароли (Argon2) и JWT-токены.

- Пароли хранятся только в виде Argon2-хеша (никаких SHA/MD5).
- JWT подписывается секретом из backend/.env (JWT_SECRET_KEY).
- Никакие пароли и токены не логируются.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

_hasher = PasswordHasher()

# auto_error=False: сами превращаем «нет заголовка» в корректный 401
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Argon2id-хеш пароля (со случайной солью)."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Проверить пароль против Argon2-хеша."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Повреждённый/неизвестный формат хеша — считаем пароль неверным
        return False


def create_access_token(user_id: int) -> str:
    """Создать JWT: sub=user_id, exp=текущее время + срок из .env."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Зависимость «текущий пользователь» из Bearer-токена.

    Проверяет: наличие заголовка Authorization, подпись JWT, срок действия,
    наличие sub и существование пользователя в БД. Любая проблема — 401.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Не авторизован. Войдите в аккаунт.")

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Сессия истекла. Войдите заново.") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Не авторизован. Войдите в аккаунт.") from None

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise _unauthorized("Не авторизован. Войдите в аккаунт.") from None

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Не авторизован. Войдите в аккаунт.")
    return user


# Удобные аннотации для защищённых endpoints
CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[Session, Depends(get_db)]


# --- Токены подтверждения email ---

def generate_verification_token() -> str:
    """Криптографически стойкий одноразовый токен (идёт пользователю в письме)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 токена: в БД храним ТОЛЬКО хеш, никогда не сам токен."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()