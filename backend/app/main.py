"""Точка входа backend-приложения Random Video."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.history import router as history_router
from app.api.routes.videos import router as videos_router
from app.config import settings

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


@app.get("/api/health")
def health_check() -> dict:
    """Простой тестовый endpoint для проверки, что сервер работает."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
