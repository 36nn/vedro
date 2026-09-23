/**
 * Страница регистрации: 4 поля, проверки на клиенте (backend валидирует
 * повторно), после успеха — автоматический вход на главную.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const MIN_PASSWORD_LENGTH = 6;

function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      // Регистрируем и сразу входим — подтверждение email не требуется
      await register(username.trim(), email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
    } finally {
      setIsLoading(false);
    }
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