import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { api } from '../services/api';

export interface Personalization {
  theme: 'light' | 'dark' | 'system';
  accent: 'blue' | 'purple' | 'green' | 'neutral';
  layout: 'comfortable' | 'compact';
  study_reminders: boolean;
  weekly_summary: boolean;
  reminder_frequency: 'daily' | 'weekly' | 'off';
  text_size: 'default' | 'large';
  dashboard_order: string[];
  preferred_study_start: string;
  timezone: string;
}

const defaults: Personalization = {
  theme: 'light',
  accent: 'blue',
  layout: 'comfortable',
  study_reminders: true,
  weekly_summary: true,
  reminder_frequency: 'weekly',
  text_size: 'default',
  dashboard_order: [],
  preferred_study_start: '18:00',
  timezone: 'Africa/Johannesburg'
};

interface PersonalizationContextValue {
  preferences: Personalization;
  loading: boolean;
  error: string | null;
  savePreferences: (value: Personalization) => Promise<void>;
}

const Context = createContext<PersonalizationContextValue | null>(null);

export function PersonalizationProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [preferences, setPreferences] = useState(defaults);
  const [loading, setLoading] = useState(Boolean(token));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!token) {
      setPreferences(defaults);
      setLoading(false);
      setError(null);
      return () => { active = false; };
    }
    setLoading(true);
    api.get<Personalization>('/preferences', token)
      .then((value) => { if (active) { setPreferences({ ...defaults, ...value }); setError(null); } })
      .catch((requestError: unknown) => {
        if (active) setError(requestError instanceof Error ? requestError.message : 'Could not load saved preferences.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    const root = document.documentElement;
    const accents = {
      blue: { primary: '#3B8292', hover: '#2E6F7D', light: '#EEF3F4', dark: '#245C68', soft: '#2C5862' },
      purple: { primary: '#7656A8', hover: '#63458F', light: '#F0EBF7', dark: '#503776', soft: '#59417D' },
      green: { primary: '#438365', hover: '#356D52', light: '#EAF3ED', dark: '#285540', soft: '#315E48' },
      neutral: { primary: '#66727A', hover: '#515D64', light: '#EFF1F2', dark: '#3E484E', soft: '#48545B' }
    }[preferences.accent];
    const rgb = (hex: string) => hex.match(/[A-Fa-f0-9]{2}/g)!.map((part) => parseInt(part, 16)).join(' ');
    root.style.setProperty('--ns-primary', accents.primary);
    root.style.setProperty('--ns-primary-rgb', rgb(accents.primary));
    root.style.setProperty('--ns-primary-hover', accents.hover);
    root.style.setProperty('--ns-primary-hover-rgb', rgb(accents.hover));
    root.style.setProperty('--ns-primary-light', accents.light);
    root.style.setProperty('--ns-primary-light-rgb', rgb(accents.light));
    root.style.setProperty('--ns-primary-dark', accents.dark);
    root.style.setProperty('--ns-primary-dark-rgb', rgb(accents.dark));
    root.style.setProperty('--ns-primary-800-rgb', rgb(accents.soft));
    root.style.setProperty('--ns-primary-900-rgb', rgb(accents.dark));
    root.style.setProperty('--ns-primary-950-rgb', rgb(accents.dark));
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const applyTheme = () => {
      root.dataset.theme = preferences.theme === 'system'
        ? (media.matches ? 'dark' : 'light')
        : preferences.theme;
    };
    applyTheme();
    media.addEventListener('change', applyTheme);
    root.dataset.layout = preferences.layout;
    root.dataset.personalizedTextSize = preferences.text_size;
    return () => media.removeEventListener('change', applyTheme);
  }, [preferences]);

  const savePreferences = async (value: Personalization) => {
    if (!token) throw new Error('Sign in to save your preferences.');
    setError(null);
    const saved = await api.put<Personalization>('/preferences', value, token);
    setPreferences({ ...defaults, ...saved });
  };

  return (
    <Context.Provider value={{ preferences, loading, error, savePreferences }}>
      {children}
    </Context.Provider>
  );
}

export function usePersonalization() {
  const value = useContext(Context);
  if (!value) throw new Error('usePersonalization must be used within PersonalizationProvider');
  return value;
}
