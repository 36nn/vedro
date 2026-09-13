/**
 * Защищённый маршрут: без авторизации — редирект на /login.
 * После входа пользователь возвращается на страницу, куда он шёл.
 */

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="page page--centered">
        <p className="home__loading">
          <span className="spinner" />
          Проверяем вход…
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

export default ProtectedRoute;