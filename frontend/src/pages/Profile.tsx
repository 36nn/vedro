/**
 * Профиль: имя, email, дата регистрации и сколько видео просмотрено.
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  const { currentUser, deleteAccount } = useAuth();
  const navigate = useNavigate();
  const [watchedCount, setWatchedCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDeleteAccount() {
    if (isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      // Аккаунт удалён на backend (история ушла каскадом), сессия очищена
      await deleteAccount();
      navigate("/", { replace: true });
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Не удалось удалить аккаунт");
      setIsDeleting(false);
    }
  }

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

      {/* Опасная зона: безвозвратное удаление аккаунта */}
      <section className="danger-zone">
        <h2 className="danger-zone__title">Опасная зона</h2>
        <p className="danger-zone__text">
          Удаление необратимо: исчезнут аккаунт и вся история просмотров.
        </p>

        {!confirmDelete ? (
          <button
            type="button"
            className="btn btn--danger"
            onClick={() => setConfirmDelete(true)}
          >
            Удалить аккаунт
          </button>
        ) : (
          <div className="danger-zone__confirm">
            <span>Точно удалить аккаунт?</span>
            <button
              type="button"
              className="btn btn--danger"
              onClick={() => void handleDeleteAccount()}
              disabled={isDeleting}
            >
              {isDeleting ? "Удаляем…" : "Да, удалить"}
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setConfirmDelete(false)}
              disabled={isDeleting}
            >
              Отмена
            </button>
          </div>
        )}

        {deleteError && <p className="home__error">{deleteError}</p>}
      </section>
    </main>
  );
}

export default Profile;