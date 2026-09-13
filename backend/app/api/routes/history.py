"""История просмотров: сохранение, список и удаление записей."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.models import WatchHistory
from app.schemas import HistoryCountOut, HistoryCreate, HistoryOut
from app.security import CurrentUser, DBSession

router = APIRouter(prefix="/history", tags=["history"])

# Защита от дублей: повторная запись о том же ролике в течение этого окна
# (например, двойной рендер React в dev-режиме) не создаёт вторую строку
DUPLICATE_WINDOW_SECONDS = 15


@router.post("", response_model=HistoryOut, status_code=status.HTTP_201_CREATED)
def add_history(
    payload: HistoryCreate, current_user: CurrentUser, db: DBSession
) -> WatchHistory:
    """Сохранить запись о просмотре.

    user_id определяется ТОЛЬКО из JWT — frontend не может указать чужого
    пользователя. Повторный POST о том же ролике за последние
    DUPLICATE_WINDOW_SECONDS секунд возвращает существующую запись.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    duplicate = db.scalar(
        select(WatchHistory)
        .where(
            WatchHistory.user_id == current_user.id,
            WatchHistory.youtube_video_id == payload.youtube_video_id,
            WatchHistory.watched_at >= cutoff,
        )
        .limit(1)
    )
    if duplicate is not None:
        return duplicate

    record = WatchHistory(
        user_id=current_user.id,
        youtube_video_id=payload.youtube_video_id,
        title=payload.title,
        channel_title=payload.channel_title,
        thumbnail_url=payload.thumbnail_url,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[HistoryOut])
def get_history(
    current_user: CurrentUser,
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[WatchHistory]:
    """История текущего пользователя, свежие записи сверху (watched_at DESC)."""
    return list(
        db.scalars(
            select(WatchHistory)
            .where(WatchHistory.user_id == current_user.id)
            .order_by(WatchHistory.watched_at.desc(), WatchHistory.id.desc())
            .offset(skip)
            .limit(limit)
        )
    )


@router.get("/count", response_model=HistoryCountOut)
def get_history_count(current_user: CurrentUser, db: DBSession) -> HistoryCountOut:
    """Всего просмотренных видео (для страницы профиля)."""
    count = db.scalar(
        select(func.count()).select_from(WatchHistory).where(WatchHistory.user_id == current_user.id)
    )
    return HistoryCountOut(count=int(count or 0))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(record_id: int, current_user: CurrentUser, db: DBSession) -> None:
    """Удалить запись истории текущего пользователя.

    Чужую запись удалить нельзя: выборка всегда фильтруется по user_id из JWT.
    Возвращаем 404, а не 403 — так мы не раскрываем постороннему пользователю
    сам факт существования записи с таким id (стандартная практика).
    """
    record = db.scalar(
        select(WatchHistory).where(
            WatchHistory.id == record_id,
            WatchHistory.user_id == current_user.id,
        )
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись истории не найдена",
        )
    db.delete(record)
    db.commit()