import { useEffect, useState } from 'react';
import { ArrowUpRight, CheckCircle2, ClipboardList } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface QueueItem { type: string; referral_id?: string; student_id?: string; risk_level?: string; urgency?: string; strategy?: string; follow_up_date?: string | null; status?: string }
interface Briefing { summary: Record<string, number>; items: QueueItem[] }

const title = (value: string) => value.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function ActionQueue() {
  const { token } = useAuth();
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    api.get<Briefing>('/workflow/weekly-briefing', token).then(setBriefing).catch((requestError: Error) => setError(requestError.message));
  }, [token]);

  const items = briefing?.items.slice(0, 5) ?? [];
  return (
    <section className="neo-card overflow-hidden" aria-labelledby="action-queue-title">
      <div className="flex items-start justify-between gap-3 border-b border-ns-divider px-5 py-4">
        <div className="flex items-start gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-md border border-brand-100 bg-brand-50 text-brand-800"><ClipboardList size={18} /></div><div><h2 id="action-queue-title" className="font-bold text-ink">Action queue</h2><p className="mt-1 text-xs text-ink-soft">The next recorded actions that need human attention</p></div></div>
        <span className="neo-chip bg-brand-50 text-brand-800">{items.length} open</span>
      </div>
      {error ? <p role="alert" className="px-5 py-5 text-sm text-ns-danger">Action queue unavailable: {error}</p> : items.length === 0 ? <div className="px-5 py-6"><div className="flex items-center gap-2 text-sm text-ns-success"><CheckCircle2 size={17} />No urgent recorded actions this week.</div><p className="mt-2 text-xs text-ns-text-muted">New referrals and due follow-ups will appear here automatically.</p></div> : <ol className="divide-y divide-ns-divider">{items.map((item, index) => <li key={`${item.type}-${item.referral_id ?? item.student_id ?? index}`} className="flex items-center justify-between gap-3 px-5 py-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-ns-text-primary">{title(item.type)}{item.student_id ? ` · ${item.student_id}` : ''}</p><p className="mt-1 text-xs text-ns-text-secondary">{[item.risk_level && `${item.risk_level} risk`, item.urgency, item.strategy, item.follow_up_date && `Due ${item.follow_up_date}`, item.status && title(item.status)].filter(Boolean).join(' · ')}</p></div>{item.referral_id && <Link className="shrink-0 text-brand-800" to={`/advisor/cases/${item.referral_id}`} aria-label={`Open ${item.referral_id}`}><ArrowUpRight size={17} /></Link>}</li>)}</ol>}
    </section>
  );
}