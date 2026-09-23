"""Точка входа backend-приложения Random Video."""

import logging

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.history import router as history_router
from app.api.routes.videos import router as videos_router
from app.config import BASE_DIR, settings

# Логгер uvicorn: все его записи видны в Render Logs
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title=settings.app_name)

# CORS: разрешаем запросы с фронтенда (Vite dev-сервер на порту 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем маршруты
app.include_router(videos_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(history_router, prefix="/api")


def _db_host() -> str:
    """Хост БД для логов (только host:port, без учётных данных)."""
    try:
        return settings.database_url.split("@", 1)[-1].split("/", 1)[0]
    except Exception:
        return "?"


def _run_migrations() -> None:
    """Идемпотентно применить миграции Alembic при старте.

    Нужно на Render: бесплатный тариф не даёт шелла для `alembic upgrade`,
    поэтому таблицы создаются/обновляются сами при каждом деплое.
    Повторный запуск на уже применённой базе — no-op.
    """
    ini_path = BASE_DIR / "alembic.ini"
    if not ini_path.exists():
        logger.warning("alembic.ini не найден — миграции пропущены")
        return
    logger.info("Alembic: применяю миграции (БД-хост: %s)", _db_host())
    alembic_cfg = AlembicConfig(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    alembic_command.upgrade(alembic_cfg, "head")
    logger.info("Alembic: миграции применены")


@app.on_event("startup")
def on_startup() -> None:
    """При старте применяем миграции (отключается AUTO_MIGRATE=false)."""
    if not settings.auto_migrate:
        logger.info("AUTO_MIGRATE=false — миграции пропущены")
        return
    try:
        _run_migrations()
    except Exception:
        # Явно печатаем причину падения (теперь fileConfig в env.py не глушит
        # логгеры). Пароль БД не логируется: SQLAlchemy маскирует его в URL,
        # здесь выводится только хост.
        logger.exception("Не удалось применить миграции (БД-хост: %s)", _db_host())
        raise


@app.get("/api/health")
def health_check() -> dict:
    """Простой тестовый endpoint для проверки, что сервер работает."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
