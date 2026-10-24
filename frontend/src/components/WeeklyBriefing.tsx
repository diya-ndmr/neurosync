import { useEffect, useState } from 'react';
import { CalendarClock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface BriefingItem {
  type: string;
  referral_id?: string;
  student_id?: string;
  module_id?: string | null;
  risk_level?: string;
  urgency?: string;
  status?: string;
  strategy?: string;
  follow_up_date?: string | null;
  recorded_at?: string;
}

interface Briefing {
  role: string;
  period_days: number;
  summary: Record<string, number>;
  items: BriefingItem[];
  data_basis: string;
}

const label = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function WeeklyBriefing() {
  const { token } = useAuth();
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setError('Sign in to load this briefing.');
      setLoading(false);
      return;
    }
    let active = true;
    api.get<Briefing>('/workflow/weekly-briefing', token)
      .then((result) => { if (active) setBriefing(result); })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  return (
    <section className="neo-card overflow-hidden" aria-labelledby="weekly-briefing-title">
      <div className="flex items-start gap-3 border-b border-ns-divider px-5 py-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-brand-100 bg-brand-50 text-brand-800"><CalendarClock size={18} /></div>
        <div>
          <h2 id="weekly-briefing-title" className="font-bold text-ink">Weekly Intelligence</h2>
          <p className="mt-1 text-xs text-ink-soft">Recorded activity from the last 7 days</p>
        </div>
      </div>
      {loading ? <p className="px-5 py-5 text-sm text-ns-text-muted">Loading recorded activity…</p>
        : error ? <p role="alert" className="px-5 py-5 text-sm text-ns-danger">Briefing unavailable: {error}</p>
          : briefing && <div className="px-5 py-4">
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {Object.entries(briefing.summary).map(([key, value]) => <p key={key} className="text-sm text-ns-text-primary"><span className="font-semibold">{value}</span> {label(key)}</p>)}
            </div>
            {briefing.items.length > 0 && <ul className="mt-3 divide-y divide-ns-divider">{briefing.items.slice(0, 8).map((item, index) => <li key={`${item.type}-${item.referral_id ?? item.student_id ?? index}`} className="py-3 first:pt-0 last:pb-0">
              <p className="text-sm font-semibold text-ns-text-primary">{label(item.type)}{item.student_id ? ` · ${item.student_id}` : ''}</p>
              <p className="mt-1 text-xs text-ns-text-secondary">{[item.referral_id, item.module_id, item.risk_level && `${item.risk_level} risk`, item.urgency, item.strategy, item.follow_up_date && `Follow-up ${item.follow_up_date}`, item.status && label(item.status)].filter(Boolean).join(' · ')}</p>
            </li>)}</ul>}
            {briefing.items.length === 0 && <p className="mt-3 text-sm text-ns-text-muted">No matching recorded activity for this period.</p>}
            <p className="mt-4 border-t border-ns-divider pt-3 text-xs text-ns-text-muted">{briefing.data_basis}</p>
          </div>}
    </section>
  );
}
