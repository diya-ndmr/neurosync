import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Role, User } from '../types';
import { api } from '../services/api';
import { requireSupabase, supabase, supabaseErrorMessage } from '../services/supabase';

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

async function getSupabaseProfile(id: string, email: string, metadata: Record<string, unknown>): Promise<User> {
  const client = requireSupabase();
  const { data, error } = await client
    .from('profiles')
    .select('full_name, role')
    .eq('id', id)
    .single();
  if (error) {
    throw new Error(`Could not load your NeuroSync profile: ${error.message}`);
  }
  if (!data || !['student', 'lecturer', 'advisor', 'admin'].includes(data.role)) {
    throw new Error('Your account has no valid NeuroSync role. Ask an administrator to provision it.');
  }
  return {
    id,
    name: data.full_name || String(metadata.full_name || email.split('@')[0]),
    email,
    role: data.role as Role
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const initialize = async () => {
      if (import.meta.env.DEV) {
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
        return;
      }
      if (!supabase) {
        setLoading(false);
        return;
      }
      try {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          console.error('Could not restore Supabase session:', error.message);
        } else if (data.session && active) {
          setToken(data.session.access_token);
          try {
            const currentUser = await getSupabaseProfile(
              data.session.user.id,
              data.session.user.email ?? '',
              data.session.user.user_metadata
            );
            if (active) setUser(currentUser);
          } catch (profileError) {
            console.error('Could not restore NeuroSync profile:', profileError);
            await supabase.auth.signOut();
          }
        }
      } catch (error) {
        console.error('Could not initialize Supabase authentication:', error);
      } finally {
        if (active) setLoading(false);
      }
    };
    void initialize();
    return () => { active = false; };
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
    if (import.meta.env.DEV) {
      const data = await api.post<SessionResponse>('/auth/login', { email, password });
      const developmentUser: User = {
        id: data.user_id,
        name: data.name,
        email: data.email,
        role: data.role
      };
      persist(data.token, developmentUser);
      setToken(data.token);
      setUser(developmentUser);
      return developmentUser;
    }

    const client = requireSupabase();
    const { data, error } = await client.auth.signInWithPassword({ email, password });
    if (error) throw new Error(supabaseErrorMessage(error));
    if (!data.session) throw new Error('No authenticated session was returned.');
    try {
      const currentUser = await getSupabaseProfile(
        data.session.user.id,
        data.session.user.email ?? email,
        data.session.user.user_metadata
      );
      setToken(data.session.access_token);
      setUser(currentUser);
      return currentUser;
    } catch (profileError) {
      await client.auth.signOut();
      throw profileError;
    }
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

    const { error } = await requireSupabase().auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        data: { full_name: data.name },
        emailRedirectTo: `${window.location.origin}/login`
      }
    });
    if (error) throw new Error(supabaseErrorMessage(error));
    return 'Account created. Click the verification link Supabase emailed to you, then sign in.';
  };

  const logout = async () => {
    const signOutError = supabase ? (await supabase.auth.signOut()).error : null;
    if (import.meta.env.DEV) {
      localStorage.removeItem(STORAGE_KEYS.token);
      localStorage.removeItem(STORAGE_KEYS.user);
    }
    setToken(null);
    setUser(null);
    if (signOutError) throw new Error(supabaseErrorMessage(signOutError));
  };

  const updateUser = (u: User) => {
    setUser(u);
    if (import.meta.env.DEV) localStorage.setItem(STORAGE_KEYS.user, JSON.stringify(u));
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
