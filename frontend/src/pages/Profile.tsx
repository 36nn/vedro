/**
 * Профиль: имя, email, дата регистрации и сколько видео просмотрено.
 */

import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { getHistoryCount } from "../services/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Profile() {
  const { currentUser } = useAuth();
  const [watchedCount, setWatchedCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHistoryCount()
      .then((count) => {
        if (!cancelled) setWatchedCount(count);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить статистику");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!currentUser) return null; // ProtectedRoute гарантирует наличие пользователя

  return (
    <main className="page page--centered">
      <section className="profile-card">
        <div className="profile-card__avatar" aria-hidden="true">
          {currentUser.username.charAt(0).toUpperCase()}
        </div>
        <h1 className="profile-card__username">@{currentUser.username}</h1>

        <dl className="profile-card__rows">
          <div className="profile-row">
            <dt>Email</dt>
            <dd>{currentUser.email}</dd>
          </div>
          <div className="profile-row">
            <dt>Статус email</dt>
            <dd
              className={
                currentUser.email_verified ? "profile-verified" : "profile-unverified"
              }
            >
              {currentUser.email_verified
                ? "✓ Email подтверждён"
                : "⚠ Email не подтверждён"}
            </dd>
          </div>
          <div className="profile-row">
            <dt>Дата регистрации</dt>
            <dd>{formatDate(currentUser.created_at)}</dd>
          </div>
          <div className="profile-row">
            <dt>Просмотрено видео</dt>
            <dd>{watchedCount ?? "…"}</dd>
          </div>
        </dl>

        {error && <p className="home__error">{error}</p>}
      </section>
    </main>
  );
}

export default Profile;