"""Pydantic-схемы запросов и ответов (auth и история)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Запрос на регистрацию."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, value: str) -> str:
        """Имя пользователя без пробелов внутри и не пустое."""
        cleaned = value.strip()
        if not cleaned or any(ch.isspace() for ch in cleaned):
            raise ValueError("Имя пользователя не может быть пустым или содержать пробелы")
        return cleaned


class UserOut(BaseModel):
    """Данные пользователя в ответах (без password_hash!)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    email_verified: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Запрос на вход."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    """Ответ на успешный вход."""

    access_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Ответ на успешную регистрацию.

    Токен подтверждения НЕ возвращается. Единственное исключение —
    dev-режим (EMAIL_DEV_MODE=true): тогда в verification_url лежит
    ссылка для локального тестирования.
    """

    message: str
    email: str
    verification_url: str | None = None


class ResendRequest(BaseModel):
    """Запрос повторной отправки письма подтверждения."""

    email: EmailStr


class ResendResponse(BaseModel):
    """Ответ на повторную отправку письма.

    verification_url заполняется только в dev-режиме (см. RegisterResponse).
    """

    message: str
    verification_url: str | None = None


class HistoryCreate(BaseModel):
    """Запрос на сохранение записи истории."""

    youtube_video_id: str = Field(min_length=5, max_length=32)
    title: str = Field(min_length=1, max_length=300)
    channel_title: str = Field(min_length=1, max_length=255)
    thumbnail_url: str = Field(min_length=1, max_length=500)


class HistoryOut(BaseModel):
    """Запись истории в ответах."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    youtube_video_id: str
    title: str
    channel_title: str
    thumbnail_url: str
    watched_at: datetime


class HistoryCountOut(BaseModel):
    """Сколько видео просмотрено (для профиля)."""

    count: int