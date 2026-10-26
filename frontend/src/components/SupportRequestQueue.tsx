import { useEffect, useState } from 'react';
import { LifeBuoy } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from './Toast';
import { api, isApiUnavailableError } from '../services/api';
import { advisorDemoSupportRequests } from '../services/advisorDemoData';

type RequestStatus = 'OPEN' | 'ACKNOWLEDGED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
interface SupportRequestItem { id: string; student_id: string; student_name: string; request_type: string; message: string; status: RequestStatus; created_at: string }

const statuses: RequestStatus[] = ['OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];

export default function SupportRequestQueue() {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const [items, setItems] = useState<SupportRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [demoMode, setDemoMode] = useState(false);

  const load = async () => {
    if (!token) return;
    try {
      const result = await api.get<{ items: SupportRequestItem[] }>('/support-requests?status=OPEN&limit=50', token);
      setItems(result.items);
      setError('');
      setDemoMode(false);
    } catch (requestError) {
      if (user?.role === 'advisor' && isApiUnavailableError(requestError)) {
        setItems(advisorDemoSupportRequests);
        setDemoMode(true);
      } else {
        const message = requestError instanceof Error ? requestError.message : 'Could not load requests';
        setError(message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load();   }, [token, user?.role]);

  const updateStatus = async (item: SupportRequestItem, status: RequestStatus) => {
    if (demoMode) return;
    try {
      await api.patch(`/support-requests/${item.id}`, { status }, token || undefined);
      showToast(`Request marked ${status.toLowerCase().replace('_', ' ')}.`);
      await load();
    } catch (requestError) {
      showToast(requestError instanceof Error ? requestError.message : 'Could not update request.', 'error');
    }
  };

  return <section className="neo-card overflow-hidden" aria-labelledby="student-support-requests-title">
    <div className="flex items-center justify-between border-b border-ns-divider px-5 py-4">
      <div className="flex items-center gap-3"><LifeBuoy size={19} className="text-brand-800" /><div><h2 id="student-support-requests-title" className="font-bold">Student support requests</h2><p className="mt-1 text-xs text-ns-text-muted">Requests students submitted directly</p></div></div>
      <span className="neo-chip bg-brand-50 text-brand-800">{items.length} open</span>
    </div>
    {demoMode && <p role="status" className="border-b border-amber-200 bg-amber-50 px-5 py-2 text-xs text-amber-900">Demo mode · backend unavailable. Sample requests are read-only and illustrative.</p>}
    {loading ? <p className="px-5 py-5 text-sm text-ns-text-muted">Loading student requests…</p> : error ? <p role="alert" className="px-5 py-5 text-sm text-ns-danger">Requests unavailable: {error}</p> : items.length === 0 ? <p className="px-5 py-6 text-sm text-ns-text-muted">No open student support requests.</p> : <ul className="divide-y divide-ns-divider">{items.map((item) => <li key={item.id} className="flex flex-wrap items-start justify-between gap-4 px-5 py-4"><div className="min-w-0 flex-1"><p className="font-semibold text-ns-text-primary">{item.student_name} <span className="font-normal text-ns-text-muted">· {item.student_id}</span></p><p className="mt-1 text-xs font-semibold text-brand-800">{item.request_type} · {new Date(item.created_at).toLocaleString()}</p><p className="mt-2 whitespace-pre-wrap text-sm text-ns-text-secondary">{item.message}</p></div>{!demoMode && <label className="text-xs text-ns-text-muted">Status<select className="neo-input mt-1 w-full min-w-40 py-1.5 text-sm" value={item.status} onChange={(event) => void updateStatus(item, event.target.value as RequestStatus)}>{statuses.map((status) => <option key={status}>{status}</option>)}</select></label>}</li>)}</ul>}
  </section>;
}
