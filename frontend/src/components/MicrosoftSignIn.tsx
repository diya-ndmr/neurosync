import { useState } from 'react';
import { X } from 'lucide-react';

const ACCOUNTS = [
  { name: 'Sarah Johnson', email: 'sarah@university.edu', label: 'Student' },
  { name: 'Dr. Mark Thompson', email: 'lecturer@university.edu', label: 'Lecturer' },
  { name: 'Amelia Richards', email: 'advisor@university.edu', label: 'Advisor' },
  { name: 'Prof. James Carter', email: 'admin@university.edu', label: 'Admin' }
];

function MicrosoftLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 21 21" aria-hidden="true">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  );
}

interface Props {
  onSelect: (email: string) => Promise<void>;
  error?: string;
}

export default function MicrosoftSignIn({ onSelect, error }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const pick = async (email: string) => {
    setBusy(email);
    // Short delay to mimic the redirect to Microsoft and back.
    await new Promise((r) => setTimeout(r, 700));
    try {
      await onSelect(email);
    } finally {
      setBusy(null);
      setOpen(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full h-12 mt-3 flex items-center justify-center gap-3 border border-ns-divider bg-white text-[#5e5e5e] font-semibold hover:bg-gray-50 transition-colors"
      >
        <MicrosoftLogo />
        Sign in with Microsoft
      </button>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-sm bg-white text-[#1b1b1b] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <MicrosoftLogo />
                <span className="font-semibold text-[#5e5e5e]">Microsoft</span>
              </div>
              <button type="button" onClick={() => setOpen(false)} aria-label="Close" disabled={!!busy}>
                <X size={18} />
              </button>
            </div>
            <h2 className="text-xl font-semibold mb-1">Pick an account</h2>
            <p className="text-xs text-gray-500 mb-4">
              Prototype simulation: no real Microsoft login takes place. Continue to NeuroSync.
            </p>
            <ul className="divide-y divide-gray-200 border-y border-gray-200">
              {ACCOUNTS.map((a) => (
                <li key={a.email}>
                  <button
                    type="button"
                    disabled={!!busy}
                    onClick={() => pick(a.email)}
                    className="w-full text-left py-3 px-1 hover:bg-gray-100 disabled:opacity-60"
                  >
                    <div className="text-sm font-semibold">
                      {a.name} <span className="text-xs font-normal text-gray-500">· {a.label}</span>
                    </div>
                    <div className="text-xs text-gray-600">
                      {busy === a.email ? 'Signing in…' : a.email}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
            {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
          </div>
        </div>
      )}
    </>
  );
}
