import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import en from '../locales/en';
import zu from '../locales/zu';
import xh from '../locales/xh';
import af from '../locales/af';

export type Language = 'en' | 'zu' | 'xh' | 'af';
export type TextSize = 'default' | 'large' | 'extra-large';
export type Contrast = 'default' | 'high';
export type MotionPreference = 'standard' | 'reduced';
export type Transparency = 'standard' | 'reduced';

interface Preferences {
  language: Language;
  textSize: TextSize;
  contrast: Contrast;
  motion: MotionPreference;
  transparency: Transparency;
}
interface AccessibilityContextValue extends Preferences {
  setLanguage: (value: Language) => void;
  setTextSize: (value: TextSize) => void;
  setContrast: (value: Contrast) => void;
  setMotion: (value: MotionPreference) => void;
  setTransparency: (value: Transparency) => void;
  t: (key: string) => string;
}

const catalogs: Record<Language, Record<string, string>> = { en, zu, xh, af };
const defaultPreferences: Preferences = { language: 'en', textSize: 'default', contrast: 'default', motion: 'standard', transparency: 'standard' };
const Context = createContext<AccessibilityContextValue | null>(null);

function loadPreferences(storageKey: string): Preferences {
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) return { ...defaultPreferences, ...JSON.parse(stored) } as Preferences;
  } catch { /* Use defaults when saved preferences are invalid. */ }
  return defaultPreferences;
}

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const owner = user?.id || 'guest';
  const storageKey = `neurosync_preferences_${owner}`;
  const [preferences, setPreferences] = useState<Preferences>(defaultPreferences);
  const [loadedKey, setLoadedKey] = useState('');

  useEffect(() => {
    setPreferences(loadPreferences(storageKey));
    setLoadedKey(storageKey);
  }, [storageKey]);

  useEffect(() => {
    if (loadedKey === storageKey) localStorage.setItem(storageKey, JSON.stringify(preferences));
  }, [loadedKey, storageKey, preferences]);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = preferences.language === 'zu' ? 'zu' : preferences.language === 'xh' ? 'xh' : preferences.language === 'af' ? 'af' : 'en';
    root.dataset.textSize = preferences.textSize;
    root.dataset.contrast = preferences.contrast;
    root.dataset.motion = preferences.motion;
    root.dataset.transparency = preferences.transparency;
  }, [preferences]);

  const value = useMemo<AccessibilityContextValue>(() => ({
    ...preferences,
    setLanguage: (language) => setPreferences((current) => ({ ...current, language })),
    setTextSize: (textSize) => setPreferences((current) => ({ ...current, textSize })),
    setContrast: (contrast) => setPreferences((current) => ({ ...current, contrast })),
    setMotion: (motion) => setPreferences((current) => ({ ...current, motion })),
    setTransparency: (transparency) => setPreferences((current) => ({ ...current, transparency })),
    t: (key) => catalogs[preferences.language][key] || catalogs.en[key] || key
  }), [preferences]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAccessibility() {
  const context = useContext(Context);
  if (!context) throw new Error('useAccessibility must be used within AccessibilityProvider');
  return context;
}