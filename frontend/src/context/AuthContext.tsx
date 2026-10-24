import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import {
  createUserWithEmailAndPassword,
  sendEmailVerification,
  signInWithEmailAndPassword,
  signOut,
  updateProfile
} from 'firebase/auth';
import type { Role, User } from '../types';
import { api } from '../services/api';
import { firebaseAuth, firebaseErrorMessage, requireFirebaseAuth } from '../services/firebase';

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
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const STORAGE_KEYS = { token: 'neurosync_token', user: 'neurosync_user' };

interface SessionResponse {
  token: string;
  user_id: string;
  name: string;
  role: Role;
  email: string;
}

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
    let data: SessionResponse;
    if (import.meta.env.DEV) {
      data = await api.post<SessionResponse>('/auth/login', { email, password });
    } else {
      const auth = requireFirebaseAuth();
      const credential = await signInWithEmailAndPassword(auth, email, password).catch((error: unknown) => {
        throw new Error(firebaseErrorMessage(error));
      });
      if (!credential.user.emailVerified) {
        try {
          await sendEmailVerification(credential.user);
        } catch (error) {
          throw new Error(firebaseErrorMessage(error));
        } finally {
          await signOut(auth);
        }
        throw new Error('Verify your email using the link Firebase sent before signing in.');
      }
      const idToken = await credential.user.getIdToken();
      try {
        data = await api.post<SessionResponse>('/auth/firebase-session', { id_token: idToken });
      } catch (error) {
        await signOut(auth);
        throw error;
      }
    }
    const u: User = { id: data.user_id, name: data.name, email: data.email, role: data.role };
    persist(data.token, u);
    setToken(data.token);
    setUser(u);
    return u;
  };

  const loginWithMicrosoft = async (email: string): Promise<User> => {
    if (!import.meta.env.DEV) {
      throw new Error('Microsoft sign-in is not configured.');
    }
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
    if (import.meta.env.DEV) {
      const result = await api.post<{ message: string }>('/auth/register', data);
      return result.message;
    }

    const auth = requireFirebaseAuth();
    try {
      const credential = await createUserWithEmailAndPassword(auth, data.email, data.password);
      await updateProfile(credential.user, { displayName: data.name });
      await sendEmailVerification(credential.user);
    } catch (error) {
      throw new Error(firebaseErrorMessage(error));
    } finally {
      await signOut(auth);
    }
    return 'Account created. Click the verification link Firebase emailed to you, then sign in.';
  };

  const logout = async () => {
    if (firebaseAuth) {
      await signOut(requireFirebaseAuth());
    }
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
