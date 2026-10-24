import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { CheckCircle2, X } from 'lucide-react';

type ToastTone = 'success' | 'error' | 'info';
interface Toast { id: number; message: string; tone: ToastTone }
interface ToastContextValue { showToast: (message: string, tone?: ToastTone) => void }

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const value = useMemo(() => ({
    showToast: (message: string, tone: ToastTone = 'success') => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current, { id, message, tone }]);
      window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4500);
    }
  }), []);

  return <ToastContext.Provider value={value}>
    {children}
    <div className="fixed bottom-5 right-5 z-[120] flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
      {toasts.map((toast) => <div key={toast.id} role={toast.tone === 'error' ? 'alert' : 'status'} aria-live={toast.tone === 'error' ? 'assertive' : 'polite'} className={`flex items-start gap-3 rounded-lg border bg-white p-3 text-sm shadow-lg ${toast.tone === 'error' ? 'border-red-200 text-red-800' : toast.tone === 'info' ? 'border-sky-200 text-sky-800' : 'border-emerald-200 text-emerald-800'}`}>
        <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
        <span className="flex-1">{toast.message}</span>
        <button type="button" className="-mr-2 -mt-2 flex min-h-11 min-w-11 items-center justify-center rounded-md" aria-label="Dismiss notification" onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}><X size={16} /></button>
      </div>)}
    </div>
  </ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}
