import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Role, User } from '../types';
import { api } from '../services/api';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  loginWithMicrosoft: (email: string) => Promise<User>;
  register: (data: {
    name: string;
    email: string;
    password: string;
    role: Role;
  }) => Promise<string>;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const STORAGE_KEYS = { token: 'neurosync_token', user: 'neurosync_user' };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem(STORAGE_KEYS.token);
    const storedUser = localStorage.getItem(STORAGE_KEYS.user);
    if (storedToken && storedUser) {
      setToken(storedToken);
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem(STORAGE_KEYS.user);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => {
      localStorage.removeItem(STORAGE_KEYS.token);
      localStorage.removeItem(STORAGE_KEYS.user);
      setToken(null);
      setUser(null);
    };
    window.addEventListener('neurosync:session-expired', handleSessionExpired);
    return () => window.removeEventListener('neurosync:session-expired', handleSessionExpired);
  }, []);

  const persist = (t: string, u: User) => {
    localStorage.setItem(STORAGE_KEYS.token, t);
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(u));
  };

  const login = async (email: string, password: string): Promise<User> => {
    const data = await api.post<{ token: string; user_id: string; name: string; role: Role }>('/auth/login', {
      email,
      password
    });
    const u: User = { id: data.user_id, name: data.name, email, role: data.role };
    persist(data.token, u);
    setToken(data.token);
    setUser(u);
    return u;
  };

  const loginWithMicrosoft = async (email: string): Promise<User> => {
    const data = await api.post<{ token: string; user_id: string; name: string; role: Role }>(
      '/auth/sso/microsoft/mock',
      { email }
    );
    const u: User = { id: data.user_id, name: data.name, email, role: data.role };
    persist(data.token, u);
    setToken(data.token);
    setUser(u);
    return u;
  };

  const register = async (data: {
    name: string;
    email: string;
    password: string;
    role: Role;
  }): Promise<string> => {
    const result = await api.post<{ message: string }>('/auth/register', data);
    return result.message;
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEYS.token);
    localStorage.removeItem(STORAGE_KEYS.user);
    setToken(null);
    setUser(null);
  };

  const updateUser = (u: User) => {
    setUser(u);
    localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(u));
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, loginWithMicrosoft, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
