import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Archive, LoaderCircle, RotateCcw, Search } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { LmsReferral } from '../../types';
import { riskBg } from '../../utils/helpers';
import { useToast } from '../../components/Toast';

interface AdvisorQueue { summary: Record<string, number>; items: LmsReferral[] }

export default function Cases() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const location = useLocation();
  const [items, setItems] = useState<LmsReferral[]>([]);
  const [query, setQuery] = useState(() => (location.state as { globalSearch?: string } | null)?.globalSearch || '');
  const [view, setView] = useState<'active' | 'archived' | 'all'>('active');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const globalSearch = (location.state as { globalSearch?: string } | null)?.globalSearch;
    if (globalSearch) setQuery(globalSearch);
  }, [location.state]);

  useEffect(() => {
    let active = true;
    api.get<AdvisorQueue>(`/workflow/advisor/dashboard${view === 'active' ? '' : '?include_closed=true'}`, token || undefined)
      .then((response) => { if (active) setItems(response.items); })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, view]);

  const filtered = items.filter((item) => (view === 'all' || (view === 'archived' ? item.status === 'CLOSED' : item.status !== 'CLOSED')) && `${item.student_name || ''} ${item.student_id} ${item.referral_id} ${item.reason} ${item.status}`.toLowerCase().includes(query.toLowerCase()));

  const setArchived = async (item: LmsReferral, archived: boolean) => {
    if (archived && !window.confirm(`Archive completed case ${item.referral_id}? It will remain in the records and can be restored from Archived.`)) return;
    try {
      await api.patch(`/workflow/advisor/referrals/${item.referral_id}/status`, { status: archived ? 'CLOSED' : 'RESOLVED' }, token || undefined);
      showToast(archived ? 'Case archived; history is retained.' : 'Case restored to active records.');
      const result = await api.get<AdvisorQueue>(`/workflow/advisor/dashboard${view === 'active' ? '' : '?include_closed=true'}`, token || undefined);
      setItems(result.items);
    } catch (requestError) {
      showToast(requestError instanceof Error ? requestError.message : 'Could not update case archive status.', 'error');
    }
  };
  return <div className="space-y-5">
    <header className="neo-card p-6"><h1 className="text-2xl font-bold">Student referrals</h1><p className="mt-1 text-sm text-ns-text-secondary">Persisted referrals in your authorised advisor scope.</p></header>
    <section className="neo-card p-5"><div className="mb-4 flex flex-wrap items-center gap-3"><div className="flex gap-2" aria-label="Referral archive view">{(['active', 'archived', 'all'] as const).map((filter) => <button key={filter} type="button" onClick={() => setView(filter)} className={`rounded-md border px-3 py-1.5 text-xs font-semibold capitalize ${view === filter ? 'border-brand-700 bg-brand-700 text-white' : 'border-ns-border bg-white text-ns-text-secondary'}`}>{filter}</button>)}</div><div className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-ns-border bg-white px-3 py-2"><Search size={16} className="text-ns-text-muted" /><input className="w-full border-0 bg-transparent p-1 text-sm focus:outline-none" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search student, referral, reason, or status" /></div></div>
      {loading && <div className="flex items-center justify-center gap-2 py-10 text-sm text-ns-text-muted"><LoaderCircle className="animate-spin" size={17} />Loading referrals…</div>}
      {error && <p role="alert" className="py-4 text-sm text-ns-danger">{error}</p>}
      {!loading && !error && <div className="overflow-x-auto"><table className="ns-table min-w-[900px]"><thead><tr><th>Student</th><th>Referral</th><th>Risk</th><th>Reason</th><th>Urgency</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{filtered.map((item) => <tr key={item.referral_id}><td>{item.student_name || item.student_id}</td><td>{item.referral_id}</td><td><span className={`neo-chip ${riskBg(item.risk_level as 'LOW' | 'MEDIUM' | 'HIGH')}`}>{item.risk_level} · {item.risk_score}%</span></td><td className="max-w-[300px]">{item.reason}</td><td>{item.urgency}</td><td>{item.status.replace(/_/g, ' ')}</td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><div className="flex items-center gap-3"><Link className="font-semibold text-brand-800 hover:underline" to={`/advisor/cases/${item.referral_id}`}>Review</Link>{item.status === 'CLOSED' ? <button type="button" className="inline-flex items-center gap-1 text-xs text-brand-800" onClick={() => void setArchived(item, false)}><RotateCcw size={14} />Restore</button> : item.status === 'RESOLVED' ? <button type="button" className="inline-flex items-center gap-1 text-xs text-ns-text-secondary" onClick={() => void setArchived(item, true)}><Archive size={14} />Archive</button> : null}</div></td></tr>)}</tbody></table></div>}
      {!loading && !error && filtered.length === 0 && <p className="py-10 text-center text-sm text-ns-text-muted">No referrals match this search.</p>}
    </section>
  </div>;
}
