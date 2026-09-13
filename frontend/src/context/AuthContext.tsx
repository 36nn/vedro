/**
 * AuthContext: текущий пользователь + login/register/logout.
 * Без Redux/Zustand — обычный React Context, как и требовалось.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  AuthUser,
  clearToken,
  getCurrentUser,
  getToken,
  login as apiLogin,
  register as apiRegister,
  RegisterResult,
} from "../services/api";

interface AuthContextValue {
  currentUser: AuthUser | null;
  isAuthenticated: boolean;
  /** Идёт проверка сохранённого токена при открытии сайта */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<RegisterResult>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function AuthProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // При открытии сайта восстанавливаем сессию из сохранённого токена:
  // токен есть -> GET /api/auth/me -> пользователь; 401 -> токен просрочен
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    getCurrentUser()
      .then(setCurrentUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    // apiLogin сохраняет токен и сразу запрашивает /me
    const user = await apiLogin(email, password);
    setCurrentUser(user);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    // Автовход отключён: пока email не подтверждён по ссылке из письма,
    // backend не выдаёт JWT (403). Страница регистрации сама покажет экран
    // «Проверьте почту» с кнопкой повторной отправки.
    return await apiRegister({ username, email, password });
  }, []);

  const logout = useCallback(() => {
    // Stateless JWT: «выход» — просто удаляем токен на клиенте
    clearToken();
    setCurrentUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      currentUser,
      isAuthenticated: currentUser !== null,
      loading,
      login,
      register,
      logout,
    }),
    [currentUser, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth должен использоваться внутри AuthProvider");
  }
  return context;
}

export { AuthProvider, useAuth };