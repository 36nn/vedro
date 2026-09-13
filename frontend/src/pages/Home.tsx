import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import RandomVideoButton from "../components/RandomVideoButton";
import VideoPlayer from "../components/VideoPlayer";
import ModeSwitcher from "../components/ModeSwitcher";
import { addHistory, getRandomVideo, VideoMode, YouTubeVideo } from "../services/api";
import { useAuth } from "../context/AuthContext";

function Home() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  const [mode, setMode] = useState<VideoMode>("all");
  const [video, setVideo] = useState<YouTubeVideo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Защита от дублей в истории: ID последнего видео, для которого уже
  // отправили POST /api/history в этой сессии (backend дополнительно
  // дедуплицирует повторы за 15 секунд)
  const postedVideoIdRef = useRef<string | null>(null);

  const loadVideo = useCallback(async (nextMode: VideoMode) => {
    setIsLoading(true);
    setError(null);

    try {
      setVideo(await getRandomVideo(nextMode));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Открытие видео из истории: /history -> «Смотреть снова» -> state.video
  useEffect(() => {
    const fromHistory = (location.state as { video?: YouTubeVideo } | null)?.video;
    if (fromHistory?.video_id) {
      setVideo(fromHistory);
      // Чистим state, чтобы видео не «воскресало» при рефреше страницы
      window.history.replaceState({}, "");
    }
    // Только при монтировании страницы
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // История просмотров: считаем просмотр начавшимся, когда YouTube-плеер
  // успешно загрузился в iframe (простой MVP вместо YouTube IFrame API).
  // Сохраняем только для авторизованных и не дублируем один и тот же ролик.
  const handlePlaybackStart = useCallback(
    (currentVideo: YouTubeVideo) => {
      if (!isAuthenticated) return;
      if (postedVideoIdRef.current === currentVideo.video_id) return;
      postedVideoIdRef.current = currentVideo.video_id;
      void addHistory({
        youtube_video_id: currentVideo.video_id,
        title: currentVideo.title,
        channel_title: currentVideo.channel_title,
        thumbnail_url: currentVideo.thumbnail_url,
      }).catch(() => {
        // Не мешаем просмотру, если запись не сохранилась (например,
        // сессия истекла) — разрешаем повторную попытку для этого видео
        postedVideoIdRef.current = null;
      });
    },
    [isAuthenticated],
  );

  // Клавиатура: → или пробел — следующее видео (на экране просмотра)
  useEffect(() => {
    if (!video) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      if (event.key !== "ArrowRight" && event.code !== "Space") return;
      event.preventDefault();
      if (!isLoading) void loadVideo(mode);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [video, isLoading, mode, loadVideo]);

  function handleModeChange(next: VideoMode) {
    if (next === mode) return;
    setMode(next);
    // На экране просмотра сразу показываем видео выбранного типа,
    // на стартовом экране просто запоминаем выбор до нажатия кнопки
    if (video) void loadVideo(next);
  }

  const modeSwitcher = (
    <ModeSwitcher mode={mode} onChange={handleModeChange} disabled={isLoading} />
  );

  // --- Стартовый экран: только название, описание, тип и большая кнопка ---
  if (!video) {
    return (
      <main className="home home--hero">
        <h1 className="home__title">
          <span className="home__title-accent">Vedro</span>
        </h1>
        <p className="home__subtitle">
          Одно нажатие — и YouTube покажет случайный ролик из тысяч
        </p>

        {modeSwitcher}

        <RandomVideoButton
          onClick={() => void loadVideo(mode)}
          disabled={isLoading}
        />

        {isLoading && (
          <p className="home__loading">
            <span className="spinner" />
            Ищем для тебя что-то интересное…
          </p>
        )}

        {error && (
          <>
            <p className="home__error">{error}</p>
            <p className="home__error-hint">
              Проверь, что запущен backend, и попробуй ещё раз
            </p>
          </>
        )}
      </main>
    );
  }

  // --- Экран просмотра: видео в рамке + стрелка рядом с ней ---
  return (
    <main className="home home--watch">
      <div className="watch-row">
        <div
          className={`video-shell${video.is_short ? " video-shell--shorts" : ""}`}
          key={video.video_id}
        >
          <VideoPlayer
            videoId={video.video_id}
            onLoaded={() => handlePlaybackStart(video)}
          />

          {isLoading && (
            <div className="video-shell__loading">
              <span className="spinner spinner--light" />
            </div>
          )}
        </div>

        {/* Стрелка спрятана за рамкой: при наведении на правый край
            выезжает из-за видео вбок, не перекрывая его */}
        <div className="edge-zone">
          <button
            type="button"
            className="next-arrow"
            onClick={() => void loadVideo(mode)}
            disabled={isLoading}
            aria-label="Следующее видео"
            title="Следующее видео"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      <section
        className={`watch-info${isLoading ? " watch-info--dim" : ""}`}
        key={video.video_id}
      >
        <span
          className={`video-badge ${
            video.is_short ? "video-badge--shorts" : "video-badge--video"
          }`}
        >
          <span className="video-badge__dot" aria-hidden="true" />
          {video.is_short ? "Shorts" : "Видео"}
        </span>
        <h2 className="watch-info__title">{video.title}</h2>
        <p className="watch-info__channel">{video.channel_title}</p>
      </section>

      {modeSwitcher}

      {isAuthenticated ? (
        <p className="watch-hint">
          Стрелка у правого края или клавиши <kbd>→</kbd> / <kbd>Space</kbd> —
          следующее видео
        </p>
      ) : (
        <p className="watch-hint">
          <Link to="/login" className="watch-hint__link">
            Войдите
          </Link>
          , чтобы сохранять историю просмотров
        </p>
      )}

      {error && <p className="home__error">{error}</p>}
    </main>
  );
}

export default Home;
