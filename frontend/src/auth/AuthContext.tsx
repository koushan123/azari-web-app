import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, configureApi } from "../services/api";
import type { User } from "../types/api";

interface AuthState { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void; can: (permission: string) => boolean }
const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = "azari_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(token));
  const logout = useCallback(() => { sessionStorage.removeItem(TOKEN_KEY); setToken(null); setUser(null); }, []);
  useEffect(() => configureApi(() => token, logout), [token, logout]);
  useEffect(() => {
    if (!token) { setLoading(false); return; }
    setLoading(true); api.me().then(setUser).catch(logout).finally(() => setLoading(false));
  }, [token, logout]);
  const login = useCallback(async (email: string, password: string) => { const result = await api.login(email, password); sessionStorage.setItem(TOKEN_KEY, result.access_token); setToken(result.access_token); configureApi(() => result.access_token, logout); setUser(await api.me()); }, [logout]);
  const value = useMemo<AuthState>(() => ({ user, loading, login, logout, can: (permission) => Boolean(user?.permissions.includes(permission)) }), [user, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider is missing"); return value; }
