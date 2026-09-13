"""Маршруты для работы с видео (YouTube Data API v3)."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import video_service
from app.services.video_service import (
    YouTubeAPIError,
    YouTubeConfigError,
    YouTubeQuotaError,
)

router = APIRouter(prefix="/videos", tags=["videos"])

# Режимы выборки: все видео / только обычные / только шортсы
VideoMode = Literal["all", "video", "shorts"]


class RandomVideoResponse(BaseModel):
    """Информация о случайном YouTube-видео."""

    video_id: str
    title: str
    channel_title: str
    description: str
    thumbnail_url: str
    youtube_url: str
    # true — это шортс (короткий вертикальный ролик)
    is_short: bool = False


@router.get("/random", response_model=RandomVideoResponse)
async def get_random_video(
    mode: VideoMode = Query(
        "all",
        description="all — любые видео, video — только обычные, shorts — только шортсы",
    ),
) -> RandomVideoResponse:
    """Вернуть случайное YouTube-видео для показа во встроенном плеере."""
    try:
        data = await video_service.get_random_youtube_video(mode=mode)
    except YouTubeConfigError as exc:
        # Проблема конфигурации на стороне сервера (ключ не настроен)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except YouTubeQuotaError as exc:
        # Квота YouTube исчерпана, а кэш пуст — просим подождать сброса квоты
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except YouTubeAPIError as exc:
        # YouTube API недоступен или вернул ошибку
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RandomVideoResponse(**data)
