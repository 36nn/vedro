/**
 * Большая кнопка в форме логотипа YouTube (чёрно-оранжевая):
 * фирменный скруглённый прямоугольник с треугольником play.
 */

interface RandomVideoButtonProps {
  /** Обработчик клика — запрос случайного видео */
  onClick: () => void;
  /** Блокировка на время загрузки видео */
  disabled?: boolean;
}

function RandomVideoButton({ onClick, disabled = false }: RandomVideoButtonProps) {
  return (
    <button
      type="button"
      className="random-video-button"
      aria-label="Случайное видео"
      onClick={onClick}
      disabled={disabled}
    >
      <svg
        className="random-video-button__logo"
        viewBox="0 0 68 48"
        aria-hidden="true"
        focusable="false"
      >
        {/* Корпус кнопки — форма логотипа YouTube */}
        <path
          className="random-video-button__body"
          d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.63-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z"
        />
        {/* Треугольник play */}
        <path className="random-video-button__play" d="M45 24 27 14v20" />
      </svg>
    </button>
  );
}

export default RandomVideoButton;
