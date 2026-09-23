"""Модели БД: пользователи и история просмотров."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    history: Mapped[list["WatchHistory"]] = relationship(
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