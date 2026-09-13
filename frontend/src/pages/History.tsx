/**
 * История просмотров: список записей, удаление, «смотреть снова».
 */

import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HistoryRecord, deleteHistory, getHistory } from "../services/api";
import type { YouTubeVideo } from "../services/api";

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function History() {
  const navigate = useNavigate();
  const [records, setRecords] = useState<HistoryRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setRecords(await getHistory(0, 50));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить историю");
      setRecords([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDelete(recordId: number) {
    setDeletingId(recordId);
    try {
      await deleteHistory(recordId);
      // Убираем запись из списка без перезагрузки страницы
      setRecords((prev) => (prev ? prev.filter((record) => record.id !== recordId) : prev));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить запись");
    } finally {
      setDeletingId(null);
    }
  }

  /** Открыть ролик на главной (Random Video покажет его в плеере). */
  function handleWatch(record: HistoryRecord) {
    const video: YouTubeVideo = {
      video_id: record.youtube_video_id,
      title: record.title,
      channel_title: record.channel_title,
      thumbnail_url: record.thumbnail_url,
      description: "",
      youtube_url: `https://www.youtube.com/watch?v=${record.youtube_video_id}`,
      is_short: false,
    };
    navigate("/", { state: { video } });
  }

  if (records === null) {
    return (
      <main className="page page--centered">
        <p className="home__loading">
          <span className="spinner" />
          Загружаем историю…
        </p>
      </main>
    );
  }

  return (
    <main className="page">
      <h1 className="page__title">История просмотров</h1>

      {error && <p className="home__error">{error}</p>}

      {records.length === 0 ? (
        <p className="history__empty">Вы ещё не посмотрели ни одного видео.</p>
      ) : (
        <ul className="history-list">
          {records.map((record) => (
            <li key={record.id} className="history-item">
              <button
                type="button"
                className="history-item__main"
                onClick={() => handleWatch(record)}
                title="Смотреть снова"
              >
                <img
                  className="history-item__thumb"
                  src={record.thumbnail_url}
                  alt=""
                  loading="lazy"
                />
                <span className="history-item__meta">
                  <span className="history-item__title">{record.title}</span>
                  <span className="history-item__channel">{record.channel_title}</span>
                  <span className="history-item__date">
                    {formatDateTime(record.watched_at)}
                  </span>
                </span>
              </button>
              <button
                type="button"
                className="history-item__delete"
                onClick={() => handleDelete(record.id)}
                disabled={deletingId === record.id}
                aria-label="Удалить из истории"
                title="Удалить из истории"
              >
                {deletingId === record.id ? "…" : "✕"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default History;