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
  deleteAccount as apiDeleteAccount,
  getCurrentUser,
  getToken,
  login as apiLogin,
  register as apiRegister,
} from "../services/api";

interface AuthContextValue {
  currentUser: AuthUser | null;
  isAuthenticated: boolean;
  /** Идёт проверка сохранённого токена при открытии сайта */
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  /** Полностью удаляет аккаунт и разлогинивает */
  deleteAccount: () => Promise<void>;
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
    // Регистрируем и сразу входим — подтверждение email не требуется
    const user = await apiRegister({ username, email, password });
    setCurrentUser(user);
  }, []);

  const deleteAccount = useCallback(async () => {
    // Удаляем аккаунт на backend (история уйдёт каскадом), затем чистим сессию
    await apiDeleteAccount();
    clearToken();
    setCurrentUser(null);
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
      deleteAccount,
      logout,
    }),
    [currentUser, loading, login, register, deleteAccount, logout],
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