"""Конфигурация приложения Random Video (pydantic-settings).

Значения читаются из переменных окружения и файла backend/.env
(список переменных — в backend/.env.example).
"""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Каталог backend/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Настройки приложения."""

    # Название приложения
    app_name: str = "Random Video"

    # Параметры запуска сервера
    host: str = "127.0.0.1"
    port: int = 8000

    # Разрешённые источники запросов (CORS). По умолчанию — локальный Vite.
    # На Render задаётся env FRONTEND_ORIGINS через запятую:
    #   FRONTEND_ORIGINS=https://vedro-frontend.onrender.com
    frontend_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Автоматически применять миграции Alembic при старте. Нужно на Render:
    # на бесплатном тарифе нет доступа к шеллу для `alembic upgrade`.
    # Отключается через env AUTO_MIGRATE=false.
    auto_migrate: bool = True

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def _split_frontend_origins(cls, value):
        """Позволить FRONTEND_ORIGINS в виде строки через запятую."""
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return value

    # Ключ YouTube Data API v3. Хранится только на backend (в .env)
    # и никогда не попадает во frontend.
    youtube_api_key: str = ""

    # Дополнительные ключи через запятую — суточные квоты всех ключей
    # складываются, ключи используются по кругу.
    youtube_api_keys: str = ""

    # --- База данных (PostgreSQL) ---
    # Строка подключения; пароль БД — только в backend/.env
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/vedro"

    # --- JWT ---
    # Секрет подписи токенов — только в backend/.env (см. .env.example)
    jwt_secret_key: str = "change_this_secret"
    jwt_algorithm: str = "HS256"
    # Срок жизни access-токена в минутах (1440 = 24 часа)
    jwt_access_token_expire_minutes: int = 1440

    # --- Email (Resend) ---
    # API-ключ Resend — только в backend/.env. Пустой = письма не отправляются
    # (dev-режим без почты, регистрация всё равно работает)
    resend_api_key: str = ""
    # От чьего имени отправляются письма (в dev — дефолтный отправитель Resend)
    email_from: str = "Vedro <onboarding@resend.dev>"
    # База адресов фронта: из неё строится ссылка подтверждения в письме
    app_base_url: str = "http://localhost:5173"
    # Срок действия токена подтверждения email, минут
    email_verification_token_expire_minutes: int = 60

    # DEV-режим: письма через Resend не отправляются, а ссылка подтверждения
    # показывается прямо в API-ответе/на сайте (для локальных тестов с любыми
    # email). В production обязательно false!
    email_dev_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def youtube_keys(self) -> list[str]:
        """Все ключи YouTube API без дублей, в порядке указания."""
        raw = [self.youtube_api_key, *self.youtube_api_keys.split(",")]
        keys = [k.strip() for k in raw if k.strip()]
        unique: list[str] = []
        for key in keys:
            if key not in unique:
                unique.append(key)
        return unique


settings = Settings()
