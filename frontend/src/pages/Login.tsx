/**
 * Страница входа: email + пароль, загрузка, обработка ошибок.
 */

import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isLoading) return;
    setIsLoading(true);
    setError(null);

    try {
      await login(email.trim(), password);
      // Возвращаем пользователя туда, куда он шёл (по умолчанию — на главную)
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
    } finally {
      setIsLoading(false);
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