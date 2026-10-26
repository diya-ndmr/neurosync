import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowRight, Cable, Database, RefreshCw } from 'lucide-react';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { DEMO_DATA_NOTICE, DEMO_INTEGRATION_ACTIVITY } from './adminDemoData';

interface ImportEvent {
  event_id: string;
  dataset: string;
  outcome: string;
  occurred_at: string;
  validation_error: boolean;
  invalid_rows: number;
  persisted_rows: number;
  errors: { row: number; field: string | null; code: string; message: string }[];
  errors_truncated: boolean;
}

interface IntegrationsData {
  api_status: string;
  application_database_status: string;
  lms_database_status: string;
  moodle: {
    configured: boolean;
    base_url: string | null;
    connection_status: string;
    last_successful_sync: string | null;
    sync_available: boolean;
    sync_unavailable_reason: string;
  };
  csv_import_history: ImportEvent[];
}

interface MoodleTest {
  connected: boolean;
  site_name: string;
  release: string | null;
}

interface IntegrationImportRow extends ImportEvent {
  is_demo?: boolean;
}

function Status({ value }: { value: string }) {
  const connected = value === 'connected';
  const label = value.replace(/_/g, ' ');
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${connected ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>{label}</span>;
}

export default function Integrations() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [data, setData] = useState<IntegrationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [moodleTest, setMoodleTest] = useState<MoodleTest | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await api.get<IntegrationsData>('/admin/integrations', token || undefined));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load integration status.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const testMoodle = async () => {
    setTesting(true);
    setMoodleTest(null);
    setError('');
    try {
      const result = await api.post<MoodleTest>('/moodle/test', {}, token || undefined);
      setMoodleTest(result);
      showToast('Moodle connection test succeeded.', 'success');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Moodle connection test failed.';
      setError(message);
      showToast(message, 'error');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="neo-card flex items-center gap-3 p-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-brand-100 bg-brand-50 text-brand-800"><Cable size={24} /></div>
        <div>
          <h1 className="text-2xl font-extrabold text-ink">Integrations</h1>
          <p className="text-sm text-ink-soft">Connection health, CSV imports and synchronization readiness</p>
        </div>
      </header>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-ns-danger">{error}</div>}
      {loading && <div className="neo-card p-5 text-sm text-ink-soft">Checking integration status…</div>}

      {data && !loading && (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <div className="neo-card p-5">
              <div className="flex items-center gap-2"><Activity size={18} className="text-brand-800" /><h2 className="font-bold text-ink">NeuroSync API</h2></div>
              <p className="mt-3"><Status value={data.api_status} /></p>
            </div>
            <div className="neo-card p-5">
              <div className="flex items-center gap-2"><Database size={18} className="text-brand-800" /><h2 className="font-bold text-ink">Application database</h2></div>
              <p className="mt-3"><Status value={data.application_database_status} /></p>
            </div>
            <div className="neo-card p-5">
              <div className="flex items-center gap-2"><Database size={18} className="text-brand-800" /><h2 className="font-bold text-ink">LMS database</h2></div>
              <p className="mt-3"><Status value={data.lms_database_status} /></p>
            </div>
          </section>

          <section className="neo-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2"><Cable size={18} className="text-brand-800" /><h2 className="font-bold text-ink">Moodle</h2></div>
                <p className="mt-2"><Status value={moodleTest?.connected ? 'connected' : data.moodle.connection_status} /></p>
                <p className="mt-2 text-sm text-ink-soft">{data.moodle.configured ? `Configured at ${data.moodle.base_url}` : 'Not configured. Add the Moodle URL and token to the backend environment.'}</p>
                {moodleTest && <p className="mt-2 text-sm text-ink-soft">Connection test succeeded: {moodleTest.site_name}{moodleTest.release ? ` · ${moodleTest.release}` : ''}</p>}
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="button" className="neo-btn px-3 py-2 text-sm" disabled={!data.moodle.configured || testing} onClick={() => void testMoodle()}>
                  <RefreshCw size={15} className={`mr-1.5 inline ${testing ? 'animate-spin' : ''}`} />{testing ? 'Testing…' : 'Test connection'}
                </button>
                <button type="button" className="neo-btn cursor-not-allowed px-3 py-2 text-sm opacity-50" disabled title={data.moodle.sync_unavailable_reason}>
                  Synchronise
                </button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 border-t border-ns-border pt-4 sm:grid-cols-2">
              <div><p className="text-xs font-semibold uppercase text-ink-faint">Last successful synchronisation</p><p className="mt-1 text-sm text-ink-soft">{data.moodle.last_successful_sync ? new Date(data.moodle.last_successful_sync).toLocaleString() : 'No successful sync recorded'}</p></div>
              <div><p className="text-xs font-semibold uppercase text-ink-faint">Sync status</p><p className="mt-1 text-sm text-ink-soft">{data.moodle.sync_unavailable_reason}</p></div>
            </div>
          </section>

          <section className="neo-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="font-bold text-ink">CSV upload and import history</h2><p className="mt-1 text-xs text-ink-soft">Import outcomes are recorded in the backend audit log. Rejected imports indicate validation or persistence failures.</p></div>
              <Link to="/admin/csv-data" className="inline-flex items-center gap-2 text-sm font-semibold text-brand-800">Open CSV tools <ArrowRight size={15} /></Link>
            </div>
            {data.csv_import_history.length > 0 ? (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[520px] text-left text-sm">
                  <thead><tr className="border-b border-ns-border text-xs uppercase text-ink-faint"><th className="pb-2 pr-4">Time</th><th className="pb-2 pr-4">Dataset</th><th className="pb-2">Result</th></tr></thead>
                  <tbody>{data.csv_import_history.map((event) => (
                    <tr key={event.event_id} className="border-b border-ns-border/70">
                      <td className="py-3 pr-4 text-ink-soft">{new Date(event.occurred_at).toLocaleString()}</td>
                      <td className="py-3 pr-4 capitalize">{event.dataset}</td>
                      <td className={`py-3 font-medium ${event.validation_error ? 'text-ns-danger' : event.outcome.toUpperCase() === 'SUCCESS' ? 'text-emerald-700' : 'text-ink-soft'}`}>
                        <p>{event.outcome}{event.validation_error ? ` · ${event.invalid_rows} invalid row(s)` : event.outcome.toUpperCase() === 'SUCCESS' ? ` · ${event.persisted_rows} imported` : ''}</p>
                        {event.errors.length > 0 && <ul className="mt-1 space-y-0.5 font-normal">{event.errors.slice(0, 3).map((item, index) => <li key={`${item.row}-${item.code}-${index}`}>Row {item.row}{item.field ? ` · ${item.field}` : ''}: {item.message}</li>)}</ul>}
                        {event.errors_truncated && <p className="mt-1 font-normal">Additional errors omitted.</p>}
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="mt-4 text-sm text-ink-soft">No CSV import events have been recorded.</p>}
          </section>

          <section className="neo-card border border-dashed border-brand-300 bg-brand-50/30 p-5" aria-labelledby="integration-demo-heading">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 id="integration-demo-heading" className="font-bold text-ink">Example integration workflow</h2>
                <p className="mt-1 text-xs text-amber-800">{DEMO_DATA_NOTICE}</p>
              </div>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold uppercase text-amber-900">Demo</span>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-ns-border bg-white p-4">
                <p className="text-xs font-semibold uppercase text-ink-faint">Sample Moodle workflow</p>
                <p className="mt-2 flex items-center gap-2 font-semibold text-ink"><Status value={DEMO_INTEGRATION_ACTIVITY.moodle.status.toLowerCase()} />{DEMO_INTEGRATION_ACTIVITY.moodle.site_name}</p>
                <p className="mt-2 text-sm text-ink-soft">Example last sync: {new Date(DEMO_INTEGRATION_ACTIVITY.moodle.last_sync).toLocaleString()}</p>
                <p className="mt-1 text-xs text-ink-faint">No real Moodle connection or synchronization was performed.</p>
              </div>
              <div className="rounded-lg border border-ns-border bg-white p-4">
                <p className="text-xs font-semibold uppercase text-ink-faint">Example CSV processing</p>
                <p className="mt-2 text-sm text-ink-soft">Sample records below show successful imports and validation failures to illustrate the workflow.</p>
              </div>
            </div>
            <div className="mt-4 overflow-x-auto rounded-lg border border-ns-border bg-white">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead><tr className="border-b border-ns-border text-xs uppercase text-ink-faint"><th className="px-3 py-2">Example time</th><th className="px-3 py-2">Dataset</th><th className="px-3 py-2">Example result</th></tr></thead>
                <tbody>{(DEMO_INTEGRATION_ACTIVITY.imports as IntegrationImportRow[]).map((event) => (
                  <tr key={event.event_id} className="border-b border-ns-border/70 last:border-0">
                    <td className="px-3 py-3 text-ink-soft">{new Date(event.occurred_at).toLocaleString()}</td>
                    <td className="px-3 py-3 capitalize">{event.dataset}</td>
                    <td className="px-3 py-3">
                      <p className={`font-medium ${event.validation_error ? 'text-ns-danger' : 'text-emerald-700'}`}>{event.outcome} · {event.validation_error ? `${event.invalid_rows} invalid rows` : `${event.persisted_rows} example rows`}</p>
                      {event.errors.slice(0, 2).map((item, index) => <p key={`${item.code}-${index}`} className="mt-1 text-xs text-ink-soft">Row {item.row}{item.field ? ` · ${item.field}` : ''}: {item.message}</p>)}
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
