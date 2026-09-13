# Vedro (RandomTube)

Веб-приложение: нажми большую чёрно-оранжевую кнопку в виде логотипа YouTube —
и получи случайное видео во встроенном плеере. Есть аккаунты с подтверждением
email и история просмотров.

## Возможности

- 🎲 Случайное видео через YouTube Data API v3 — режимы: **все / только видео / только Shorts**
- 🔐 Регистрация и вход по JWT, **подтверждение email** через Resend
- 📜 **История просмотров**: список с превью, удаление, «смотреть снова»
- 👤 Профиль: email, статус подтверждения, счётчик просмотров
- ⚡ Кэш поиска: одна выдача YouTube (~100 ед. квоты) обслуживает десятки показов
- 🔑 Несколько YouTube-ключей с автоматическим failover при исчерпании квоты
- ✅ Предпроверка встраиваемости (oEmbed) — «Видео недоступно» не показывается
- 📱 Тёмный адаптивный интерфейс с анимациями, клавиатура (`→`/`Space`)

## Стек

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2, Alembic, PostgreSQL, PyJWT, argon2-cffi, httpx, Resend
- **Frontend:** React 18, TypeScript, Vite, React Router

## Структура

```
backend/
├── app/
│   ├── main.py               # точка входа FastAPI (CORS, роутеры)
│   ├── config.py             # настройки из .env (pydantic-settings)
│   ├── database.py           # SQLAlchemy engine + сессия
│   ├── models.py             # User, WatchHistory, EmailVerificationToken
│   ├── schemas.py            # Pydantic-схемы
│   ├── security.py           # Argon2-пароли, JWT, get_current_user
│   ├── api/routes/           # auth.py, history.py, videos.py
│   └── services/             # video_service.py (YouTube), email_service.py (Resend)
├── alembic/                  # миграции (users, watch_history, tokens)
└── .env                      # секреты (в Git не попадает)

frontend/
└── src/
    ├── components/           # Header, RandomVideoButton, VideoPlayer, ModeSwitcher…
    ├── context/AuthContext   # login/register/logout, восстановление сессии
    ├── pages/                # Home, Login, Register, VerifyEmail, History, Profile
    └── services/api.ts       # все запросы к FastAPI (Bearer JWT)
```

## Быстрый старт

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell (Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env              # затем заполни .env (таблица ниже)
python -m alembic upgrade head      # создать таблицы в PostgreSQL
python -m uvicorn app.main:app --port 8000
```

- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

Либо двойным кликом `backend/run.bat` (после установки зависимостей).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- Приложение: http://localhost:5173
- Двойной клик `frontend/run.bat` — тоже работает.

## Переменные окружения

Скопируй `backend/.env.example` в `backend/.env` и заполни (реальные значения
никогда не коммитятся — `.env` в `.gitignore`):

| Переменная | Назначение |
|---|---|
| `YOUTUBE_API_KEY` | ключ YouTube Data API v3 (обязательно) |
| `YOUTUBE_API_KEYS` | доп. ключи через запятую — квоты складываются |
| `DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/vedro` |
| `JWT_SECRET_KEY` | секрет JWT: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | срок жизни токена (1440) |
| `RESEND_API_KEY` | ключ Resend (пусто = письма не отправляются) |
| `EMAIL_FROM` | отправитель, напр. `Vedro <onboarding@resend.dev>` |
| `APP_BASE_URL` | адрес фронта — из него строятся ссылки в письмах |
| `EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES` | срок ссылки подтверждения (60) |
| `EMAIL_DEV_MODE` | `true` — письма не шлются, ссылка показывается на сайте |
| `VITE_API_BASE_URL` *(frontend)* | адрес backend для фронта (по умолчанию `http://localhost:8000`) |

Ключи YouTube: https://console.cloud.google.com → включить «YouTube Data API v3» →
Credentials → API key. Ключи Resend: https://resend.com/api-keys.

## API

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/health` | проверка живости |
| GET | `/api/videos/random?mode=all\|video\|shorts` | случайное видео |
| POST | `/api/auth/register` | регистрация + письмо подтверждения |
| GET | `/api/auth/verify-email?token=…` | подтверждение email |
| POST | `/api/auth/resend-verification` | повторное письмо (cooldown 60 с) |
| POST | `/api/auth/login` | вход (только после подтверждения email) |
| GET | `/api/auth/me` | текущий пользователь (JWT) |
| POST/GET | `/api/history`, `/api/history/count` | история просмотров (JWT) |
| DELETE | `/api/history/{id}` | удалить свою запись (JWT) |

## Почта и режим разработки

Без подтверждённого домена Resend отправляет письма только на email владельца
аккаунта. Для локальных тестов с любыми адресами включи в `.env`
`EMAIL_DEV_MODE=true` — ссылка подтверждения будет показываться прямо на сайте.
**В production обязательно `false`.**

## Заметки о квоте YouTube

Поиск (`search.list`) стоит 100 единиц квоты, результаты кэшируются в памяти
(~2 ед. на показ). При исчерпании квоты всех ключей приложение продолжает
выдавать видео из кэша.
