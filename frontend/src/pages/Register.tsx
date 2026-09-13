/**
 * Регистрация: 4 поля, проверки на клиенте (backend валидирует повторно).
 * После успеха — экран «Проверьте почту»: автовход отключён, пока email
 * не подтверждён по ссылке из письма.
 */

import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { resendVerification } from "../services/api";

const MIN_PASSWORD_LENGTH = 6;

function Register() {
  const { register } = useAuth();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Экран «проверьте почту» после успешной регистрации
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [resendMessage, setResendMessage] = useState<string | null>(null);
  // Ссылка подтверждения — приходит только в dev-режиме (письма не шлются)
  const [devUrl, setDevUrl] = useState<string | null>(null);

  function validate(): string | null {
    if (!username.trim() || !email.trim() || !password || !confirmPassword) {
      return "Заполните все поля";
    }
    if (username.trim().length < 3) {
      return "Имя пользователя — минимум 3 символа";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return "Введите корректный email";
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      return `Пароль должен быть не короче ${MIN_PASSWORD_LENGTH} символов`;
    }
    if (password !== confirmPassword) {
      return "Пароли не совпадают";
    }
    return null;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isLoading) return;

    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await register(username.trim(), email.trim(), password);
      // Автовхода больше нет: показываем экран «проверьте почту»
      setRegisteredEmail(result.email);
      setDevUrl(result.verification_url ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResend() {
    if (!registeredEmail || resendState === "sending") return;
    setResendState("sending");
    setResendMessage(null);
    try {
      const result = await resendVerification(registeredEmail);
      setResendState("sent");
      setResendMessage(result.message);
      setDevUrl(result.verification_url ?? null);
    } catch (err) {
      setResendState("error");
      setResendMessage(err instanceof Error ? err.message : "Не удалось отправить письмо");
    }
  }

  // --- Экран «проверьте почту» после успешной регистрации ---
  if (registeredEmail) {
    return (
      <main className="page page--centered">
        <section className="auth-card">
          <h1 className="auth-card__title">Регистрация завершена!</h1>

          <p className="register-note">
            Мы отправили письмо на:
            <br />
            <b className="register-note__email">{registeredEmail}</b>
          </p>
          <p className="register-note">
            Откройте письмо и нажмите кнопку «Подтвердить email» — после этого
            можно войти в аккаунт.
          </p>

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

          {devUrl ? (
            <a className="btn btn--primary auth-card__link-as-btn" href={devUrl}>
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

          <p className="auth-card__footer">
            Уже подтвердили email?{" "}
            <Link to="/login" className="auth-card__link">
              Войти
            </Link>
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="page page--centered">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1 className="auth-card__title">Регистрация</h1>

        <label className="field">
          <span className="field__label">Имя пользователя</span>
          <input
            className="field__input"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="ivan_petrov"
            autoComplete="username"
            required
          />
        </label>

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
            placeholder={`Минимум ${MIN_PASSWORD_LENGTH} символов`}
            autoComplete="new-password"
            required
          />
        </label>

        <label className="field">
          <span className="field__label">Повторите пароль</span>
          <input
            className="field__input"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder="Ещё раз пароль"
            autoComplete="new-password"
            required
          />
        </label>

        {error && <p className="auth-card__error">{error}</p>}

        <button type="submit" className="btn btn--primary" disabled={isLoading}>
          {isLoading ? "Создаём аккаунт…" : "Создать аккаунт"}
        </button>

        <p className="auth-card__footer">
          Уже есть аккаунт?{" "}
          <Link to="/login" className="auth-card__link">
            Войти
          </Link>
        </p>
      </form>
    </main>
  );
}

export default Register;