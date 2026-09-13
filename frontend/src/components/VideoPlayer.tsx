/**
 * Плеер: показывает YouTube-видео через встроенный YouTube player (iframe).
 */

interface VideoPlayerProps {
  /** ID видео с YouTube */
  videoId: string;
  /** Вызывается, когда плеер загрузился внутри iframe (просмотр начался) */
  onLoaded?: () => void;
}

function VideoPlayer({ videoId, onLoaded }: VideoPlayerProps) {
  return (
    <iframe
      className="video-player"
      src={`https://www.youtube.com/embed/${videoId}`}
      title="YouTube video player"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      allowFullScreen
      onLoad={onLoaded}
    />
  );
}

export default VideoPlayer;
