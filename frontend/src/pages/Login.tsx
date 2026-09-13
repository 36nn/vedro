/**
 * Страница входа: email + пароль, загрузка, ошибки.
 * 403 (email не подтверждён) — отдельный блок с кнопкой повторной отправки.
 */

import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError, resendVerification } from "../services/api";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 403: email не подтверждён — предлагаем отправить письмо повторно
  const [needVerify, setNeedVerify] = useState(false);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  // Ссылка подтверждения — только в dev-режиме (письма не шлются)
  const [devLink, setDevLink] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isLoading) return;
    setIsLoading(true);
    setError(null);
    setNeedVerify(false);

    try {
      await login(email.trim(), password);
      // Возвращаем пользователя туда, куда он шёл (по умолчанию — на главную)
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
      if (err instanceof ApiError && err.status === 403) {
        setNeedVerify(true);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResend() {
    if (resendState === "sending") return;
    setResendState("sending");
    setResendMessage(null);
    try {
      const result = await resendVerification(email.trim());
      setResendState("sent");
      setResendMessage(result.message);
      setDevLink(result.verification_url ?? null);
    } catch (err) {
      setResendState("error");
      setResendMessage(err instanceof Error ? err.message : "Не удалось отправить письмо");
    }
  }

  return (
    <main className="page page--centered">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1 className="auth-card__title">Вход</h1>

        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="field__input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </label>

        <label className="field">
          <span className="field__label">Пароль</span>
          <input
            className="field__input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </label>

        {error && <p className="auth-card__error">{error}</p>}

        {needVerify && (
          <div className="verify-block">
            <p className="register-note">
              Мы отправили письмо с ссылкой подтверждения. Если вы уже нажали
              ссылку — просто войдите ещё раз.
            </p>
            {devLink ? (
              <a className="btn btn--primary auth-card__link-as-btn" href={devLink}>
                Перейти к подтверждению (dev)
              </a>
            ) : (
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void handleResend()}
                disabled={resendState === "sending"}
              >
                {resendState === "sending" ? "Отправляем…" : "Отправить письмо повторно"}
              </button>
            )}
            {resendMessage && (
              <p
                className={
                  resendState === "error"
                    ? "auth-card__error"
                    : "register-note register-note--ok"
                }
              >
                {resendMessage}
              </p>
            )}
          </div>
        )}

        <button type="submit" className="btn btn--primary" disabled={isLoading}>
          {isLoading ? "Входим…" : "Войти"}
        </button>

        <p className="auth-card__footer">
          Нет аккаунта?{" "}
          <Link to="/register" className="auth-card__link">
            Зарегистрироваться
          </Link>
        </p>
      </form>
    </main>
  );
}

export default Login;