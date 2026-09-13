/**
 * Переключатель режима выборки: Все / Видео / Шортсы.
 * Оранжевая «пилюля» плавно скользит к выбранному пункту.
 */

import { VideoMode } from "../services/api";

interface ModeSwitcherProps {
  mode: VideoMode;
  onChange: (mode: VideoMode) => void;
  disabled?: boolean;
}

const MODES: { value: VideoMode; label: string; hint: string }[] = [
  { value: "all", label: "Все", hint: "Любые ролики" },
  { value: "video", label: "Видео", hint: "Только обычные ролики" },
  { value: "shorts", label: "Шортсы", hint: "Только YouTube Shorts" },
];

function ModeSwitcher({ mode, onChange, disabled }: ModeSwitcherProps) {
  const activeIndex = MODES.findIndex((item) => item.value === mode);

  return (
    <div className="mode-switcher" role="group" aria-label="Тип видео">
      <span
        className="mode-switcher__indicator"
        style={{ transform: `translateX(${activeIndex * 100}%)` }}
        aria-hidden="true"
      />
      {MODES.map((item) => (
        <button
          key={item.value}
          type="button"
          className={`mode-switcher__option${
            item.value === mode ? " mode-switcher__option--active" : ""
          }`}
          onClick={() => onChange(item.value)}
          disabled={disabled}
          aria-pressed={item.value === mode}
          title={item.hint}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export default ModeSwitcher;