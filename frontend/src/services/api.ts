// Запросы к FastAPI backend.
// API-ключ YouTube здесь не используется — он хранится только на backend.

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

/** Режим выборки: все видео, только обычные или только шортсы. */
export type VideoMode = "all" | "video" | "shorts";

export interface YouTubeVideo {
  video_id: string;
  title: string;
  channel_title: string;
  description: string;
  thumbnail_url: string;
  youtube_url: string;
  /** true — это шортс (короткий вертикальный ролик) */
  is_short: boolean;
}

// --- Текущий пользователь (JWT) ---

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface HistoryRecord {
  id: number;
  youtube_video_id: string;
  title: string;
  channel_title: string;
  thumbnail_url: string;
  watched_at: string;
}

const TOKEN_KEY = "vedro_token";

/**
 * Компромисс MVP: JWT хранится в localStorage (доступен JS на странице,
 * то есть при XSS токен можно украсть). Безопаснее httpOnly-cookie, но для
 * локального проекта выбран простой вариант — без CSRF-защиты на backend.
 */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** Ошибка API с HTTP-статусом — страницы могут реагировать на 403/429 и т.п. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** Достать понятный текст ошибки из ответа backend. */
async function readError(response: Response, fallback: string): Promise<ApiError> {
  let detail = fallback;
  try {
    const body = (await response.json()) as { detail?: string | unknown };
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (body.detail) {
      // detail-массив — ошибки валидации FastAPI (422)
      detail = "Проверьте правильность заполнения полей";
    }
  } catch {
    // тело не JSON — оставляем общий текст
  }
  return new ApiError(response.status, detail);
}

/** Запрос с авторизацией: добавляет Authorization: Bearer TOKEN. */
async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Нет связи с сервером. Убедись, что backend запущен.");
  }
  return response;
}

// --- Случайное видео (как раньше) ---

/** Получить случайное YouTube-видео от backend. */
export async function getRandomVideo(mode: VideoMode = "all"): Promise<YouTubeVideo> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/api/videos/random?mode=${mode}`);
  } catch {
    throw new Error("Нет связи с сервером. Убедись, что backend запущен.");
  }

  if (!response.ok) {
    throw await readError(response, `Ошибка сервера: ${response.status}`);
  }

  return (await response.json()) as YouTubeVideo;
}

// --- Аутентификация ---

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

/** Зарегистрировать аккаунт (AuthContext сразу выполнит вход). */
export async function register(data: RegisterData): Promise<AuthUser> {
  const response = await authFetch("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, "Не удалось зарегистрироваться");
  }
  return (await response.json()) as AuthUser;
}

/** Войти: сохраняет токен и возвращает данные пользователя. */
export async function login(email: string, password: string): Promise<AuthUser> {
  const response = await authFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw await readError(response, "Не удалось войти");
  }
  const token = (await response.json()) as { access_token: string };
  setToken(token.access_token);
  return getCurrentUser();
}

/** Данные текущего пользователя по сохранённому токену. */
export async function getCurrentUser(): Promise<AuthUser> {
  const response = await authFetch("/api/auth/me");
  if (!response.ok) {
    throw await readError(response, "Не удалось получить профиль");
  }
  return (await response.json()) as AuthUser;
}

// --- История просмотров ---

export interface HistoryAddData {
  youtube_video_id: string;
  title: string;
  channel_title: string;
  thumbnail_url: string;
}

/** Сохранить запись о просмотре (требует авторизации). */
export async function addHistory(data: HistoryAddData): Promise<HistoryRecord> {
  const response = await authFetch("/api/history", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, "Не удалось сохранить историю");
  }
  return (await response.json()) as HistoryRecord;
}

/** История текущего пользователя (свежие сверху). */
export async function getHistory(skip = 0, limit = 20): Promise<HistoryRecord[]> {
  const response = await authFetch(`/api/history?skip=${skip}&limit=${limit}`);
  if (!response.ok) {
    throw await readError(response, "Не удалось загрузить историю");
  }
  return (await response.json()) as HistoryRecord[];
}

/** Сколько видео просмотрено всего (для профиля). */
export async function getHistoryCount(): Promise<number> {
  const response = await authFetch("/api/history/count");
  if (!response.ok) {
    throw await readError(response, "Не удалось получить статистику");
  }
  const body = (await response.json()) as { count: number };
  return body.count;
}

/** Удалить запись истории. */
export async function deleteHistory(recordId: number): Promise<void> {
  const response = await authFetch(`/api/history/${recordId}`, { method: "DELETE" });
  if (!response.ok) {
    throw await readError(response, "Не удалось удалить запись");
  }
}

/** Удалить свой аккаунт (история и токены удаляются вместе с ним). */
export async function deleteAccount(): Promise<void> {
  const response = await authFetch("/api/auth/account", { method: "DELETE" });
  if (!response.ok) {
    throw await readError(response, "Не удалось удалить аккаунт");
  }
}
