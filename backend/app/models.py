"""Модели БД: пользователи и история просмотров."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Пользователь приложения."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Имя пользователя — уникальное, показывается в интерфейсе
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # Email — уникальный, используется для входа
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # Только Argon2-хеш, открытые пароли никогда не храним
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Подтверждён ли email по ссылке из письма. До подтверждения вход запрещён
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    history: Mapped[list["WatchHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WatchHistory(Base):
    """Запись истории: какой ролик (YouTube ID) и когда смотрел пользователь.

    Мы не скачиваем видео — храним только метаданные и youtube_video_id.
    """

    __tablename__ = "watch_history"
    # Быстрый выбор истории пользователя в порядке свежести
    __table_args__ = (Index("ix_watch_history_user_watched", "user_id", "watched_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Например: dQw4w9WgXcQ
    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(500), nullable=False)
    watched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="history")


class EmailVerificationToken(Base):
    """Одноразовый токен подтверждения email.

    ВАЖНО: в БД хранится только SHA-256-хеш токена. Настоящий токен уходит
    пользователю в письме и нигде не сохраняется — утёкшая база не позволит
    подтвердить чужой email.
    """

    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SHA-256 hex (64 символа), уникальный
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="verification_tokens")