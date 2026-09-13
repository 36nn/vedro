/**
 * Верхняя навигация: бренд + вход/регистрация либо профиль/выход.
 */

import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Header() {
  const { currentUser, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <header className="header">
      <Link to="/" className="header__brand">
        <span className="header__brand-accent">Vedro</span>
      </Link>

      <nav className="header__nav">
        {isAuthenticated && currentUser ? (
          <>
            <NavLink to="/history" className="header__link">
              История
            </NavLink>
            <NavLink to="/profile" className="header__link">
              Профиль
            </NavLink>
            <span className="header__user" title={currentUser.email}>
              @{currentUser.username}
            </span>
            <button type="button" className="header__button" onClick={handleLogout}>
              Выйти
            </button>
          </>
        ) : (
          <>
            <NavLink to="/login" className="header__link">
              Войти
            </NavLink>
            <NavLink to="/register" className="header__button header__button--primary">
              Регистрация
            </NavLink>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;