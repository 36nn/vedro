"""Подключение к PostgreSQL (SQLAlchemy 2.x, синхронный движок).

URL базы читается из backend/.env (DATABASE_URL, см. .env.example).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_pre_ping: разорванные соединения (сон ПК и т.п.) восстанавливаются сами
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Базовый класс всех моделей."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия БД на время одного запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()