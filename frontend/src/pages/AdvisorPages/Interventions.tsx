import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CalendarClock, CheckCircle2, LoaderCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api, isApiUnavailableError } from '../../services/api';
import type { LmsIntervention } from '../../types';
import { useToast } from '../../components/Toast';
import { advisorDemoInterventions } from '../../services/advisorDemoData';

interface InterventionRow extends LmsIntervention {
  student_id: string;
  student_name: string;
  referral_status: string;
}

export default function Interventions() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [items, setItems] = useState<InterventionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState('');
  const [demoMode, setDemoMode] = useState(false);

  const load = async () => {
    try {
      const result = await api.get<{ items: InterventionRow[] }>('/workflow/advisor/interventions', token || undefined);
      setItems(result.items);
      setDemoMode(false);
    } catch (requestError) {
      if (isApiUnavailableError(requestError)) {
        setItems(advisorDemoInterventions);
        setDemoMode(true);
      } else {
        setError(requestError instanceof Error ? requestError.message : 'Could not load interventions');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [token]);

  const update = async (id: string, changes: Record<string, string | null>) => {
    setBusyId(id);
    setError('');
    try {
      await api.patch(`/workflow/advisor/interventions/${id}`, changes, token || undefined);
      await load();
      showToast('Intervention updated.');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not update intervention';
      setError(message);
      showToast(message, 'error');
    } finally {
      setBusyId('');
    }
  };

  const dueItems = items.filter((item) => item.status === 'FOLLOW_UP' || (item.follow_up_date && item.follow_up_date <= new Date().toISOString().slice(0, 10)));
  return <div className="space-y-5">
    <header className="neo-card p-6"><div className="flex items-center gap-3"><div className="ns-page-icon h-11 w-11"><CheckCircle2 size={21} /></div><div><h1 className="text-2xl font-bold">Interventions</h1><p className="text-sm text-ns-text-secondary">Persisted advisor-owned support strategies and review dates.</p></div></div></header>
    {demoMode && <div role="status" className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"><strong>Demo mode · backend unavailable.</strong> These intervention examples are read-only and are not saved records.</div>}
    {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-ns-danger">{error}</div>}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><Metric label="Total interventions" value={items.length} /><Metric label="Active" value={items.filter((item) => item.status === 'ACTIVE').length} /><Metric label="Follow-up due" value={dueItems.length} /><Metric label="Completed" value={items.filter((item) => item.status === 'COMPLETED').length} /></div>
    {loading ? <div className="flex justify-center gap-2 py-12 text-sm text-ns-text-muted"><LoaderCircle className="animate-spin" size={18} />Loading interventions…</div> : items.length === 0 ? <section className="neo-card p-8 text-center"><h2 className="font-semibold">No interventions assigned</h2><p className="mt-1 text-sm text-ns-text-muted">Create strategies from an advisor case after reviewing its academic context.</p><Link to="/advisor/cases" className="mt-3 inline-block text-sm font-semibold text-brand-800">Open referral queue</Link></section> : <div className="space-y-3">{items.map((item) => <article className="neo-card p-5" key={item.intervention_id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">{item.strategy}</h2><p className="mt-1 text-sm text-ns-text-secondary">{item.student_name} · {item.student_id}</p><p className="mt-2 text-sm">{item.reason}</p><p className="mt-2 text-xs text-ns-text-muted">Started {new Date(item.date_started).toLocaleDateString()} · Review {item.review_date || 'not scheduled'} · Follow-up {item.follow_up_date || 'not scheduled'}</p></div><span className={`neo-chip ${item.status === 'COMPLETED' ? 'bg-emerald-50 text-ns-success' : item.status === 'FOLLOW_UP' ? 'bg-amber-50 text-ns-warning' : 'bg-brand-50 text-brand-800'}`}>{item.status}</span></div><div className="mt-4 flex flex-wrap items-center gap-2">{!demoMode && <><label className="text-xs text-ns-text-muted">Status<select className="neo-input ml-2 w-auto py-1.5 text-sm" value={item.status} disabled={busyId === item.intervention_id} onChange={(event) => void update(item.intervention_id, { status: event.target.value })}>{['PLANNED', 'ACTIVE', 'FOLLOW_UP', 'COMPLETED', 'DISCONTINUED'].map((status) => <option key={status}>{status}</option>)}</select></label><label className="text-xs text-ns-text-muted">Follow-up<input className="neo-input ml-2 w-auto py-1.5 text-sm" type="date" value={item.follow_up_date || ''} onChange={(event) => void update(item.intervention_id, { follow_up_date: event.target.value || null, status: event.target.value ? 'FOLLOW_UP' : item.status })} /></label></>}<Link to={`/advisor/cases/${item.referral_id}`} className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-800"><CalendarClock size={15} />Open case</Link></div></article>)}</div>}
  </div>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3"><p className="text-xs text-ns-text-muted">{label}</p><p className="mt-1 text-xl font-semibold text-brand-800">{value}</p></div>;
}
