import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowUpRight, CheckCircle2, CircleHelp, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import {
  DEMO_AUDIT_EVENTS,
  DEMO_DATA_NOTICE,
  DEMO_ENCRYPTION_EXAMPLE,
  DEMO_STAFF_SECURITY,
} from './adminDemoData';

interface SecurityOverview {
  permissions: { role: string; enforcement: string }[];
  mfa: { status: string; detail: string };
  encryption: {
    production_https_required: boolean;
    frontend_https_configured: boolean;
    supabase_https_configured: boolean | null;
    database_transport: string;
    encryption_at_rest: string;
  };
  audit_log: { available: boolean; retention: string };
  data_retention: { status: string; detail: string };
  privacy_notice: { status: string; detail: string };
}

interface AuditEvent {
  event_id: string;
  actor: string;
  action: string;
  outcome: string;
  occurred_at: string;
  is_demo?: boolean;
}

interface AuditResponse {
  total: number;
  items: AuditEvent[];
}

function Status({ children, positive = false }: { children: ReactNode; positive?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${positive ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
      {positive ? <CheckCircle2 size={13} /> : <CircleHelp size={13} />}
      {children}
    </span>
  );
}

export default function SettingsPage() {
  const { token } = useAuth();
  const [security, setSecurity] = useState<SecurityOverview | null>(null);
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [securityResult, auditResult] = await Promise.all([
        api.get<SecurityOverview>('/admin/security', token || undefined),
        api.get<AuditResponse>('/admin/audit-events?limit=50', token || undefined)
      ]);
      setSecurity(securityResult);
      setAudit(auditResult);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load security and privacy information.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const displayAuditEvents = [
    ...DEMO_AUDIT_EVENTS,
    ...(audit?.items.map((event) => ({ ...event, is_demo: false })) ?? []),
  ].sort((first, second) => new Date(second.occurred_at).getTime() - new Date(first.occurred_at).getTime());

  return (
    <div className="space-y-6">
      <header className="neo-card flex flex-wrap items-center justify-between gap-4 p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-brand-100 bg-brand-50 text-brand-800">
            <ShieldCheck size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-ink">Security &amp; Privacy</h1>
            <p className="text-sm text-ink-soft">Backend-enforced controls and verified system status</p>
          </div>
        </div>
        <Link to="/admin/integrations" className="inline-flex items-center gap-2 text-sm font-semibold text-brand-800 hover:text-brand-700">
          Integrations <ArrowUpRight size={16} />
        </Link>
      </header>

      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-ns-danger">{error}</div>}
      {loading && <div className="neo-card p-5 text-sm text-ink-soft">Loading security status…</div>}

      {security && !loading && (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="neo-card p-5">
              <div className="flex items-center gap-2 text-brand-800"><ShieldCheck size={18} /><h2 className="font-bold text-ink">Role permissions</h2></div>
              <p className="mt-3"><Status positive>Backend enforced</Status></p>
              <p className="mt-2 text-xs text-ink-soft">Role checks protect API routes; resource-level scope checks also apply.</p>
            </div>
            <div className="neo-card p-5">
              <div className="flex items-center gap-2 text-brand-800"><LockKeyhole size={18} /><h2 className="font-bold text-ink">Staff MFA</h2></div>
              <p className="mt-3"><Status>Not integrated</Status></p>
              <p className="mt-2 text-xs text-ink-soft">{security.mfa.detail}</p>
            </div>
            <div className="neo-card p-5">
              <div className="flex items-center gap-2 text-brand-800"><LockKeyhole size={18} /><h2 className="font-bold text-ink">Encryption</h2></div>
              <p className="mt-3"><Status positive={security.encryption.frontend_https_configured}>Frontend {security.encryption.frontend_https_configured ? 'HTTPS' : 'not HTTPS'}</Status></p>
              <p className="mt-2 text-xs text-ink-soft">Supabase URL: {security.encryption.supabase_https_configured == null ? 'not configured' : security.encryption.supabase_https_configured ? 'HTTPS configured' : 'not HTTPS configured'}. Database transport is not verified; at-rest encryption is not verifiable by this application.</p>
            </div>
            <div className="neo-card p-5">
              <div className="flex items-center gap-2 text-brand-800"><Activity size={18} /><h2 className="font-bold text-ink">Data retention</h2></div>
              <p className="mt-3"><Status>Not configured</Status></p>
              <p className="mt-2 text-xs text-ink-soft">{security.data_retention.detail}</p>
            </div>
          </section>

          <section className="neo-card p-5">
            <h2 className="font-bold text-ink">Role-based permissions</h2>
            <p className="mt-1 text-sm text-ink-soft">These are enforced by backend authorization checks, not browser-only controls.</p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {security.permissions.map((permission) => (
                <div key={permission.role} className="rounded-lg border border-ns-border bg-white p-4">
                  <p className="font-semibold capitalize text-ink">{permission.role}</p>
                  <p className="mt-1 text-sm text-ink-soft">{permission.enforcement}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="neo-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Activity size={18} className="text-brand-800" />
                <div>
                  <h2 className="font-bold text-ink">Audit log</h2>
                  <p className="text-xs text-ink-soft">{audit?.total ?? 0} backend events · {DEMO_AUDIT_EVENTS.length} sample events · retention {security.audit_log.retention}</p>
                </div>
              </div>
              <button type="button" className="neo-btn px-3 py-2 text-sm" onClick={() => void load()}>Refresh</button>
            </div>
            {displayAuditEvents.length > 0 ? (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead><tr className="border-b border-ns-border text-xs uppercase text-ink-faint"><th className="pb-2 pr-4">Source</th><th className="pb-2 pr-4">Time</th><th className="pb-2 pr-4">Actor</th><th className="pb-2 pr-4">Action</th><th className="pb-2">Outcome</th></tr></thead>
                  <tbody>
                    {displayAuditEvents.map((event) => (
                      <tr key={event.event_id} className="border-b border-ns-border/70">
                        <td className="py-3 pr-4"><Status positive={!event.is_demo}>{event.is_demo ? 'Demo' : 'Backend'}</Status></td>
                        <td className="py-3 pr-4 text-ink-soft">{new Date(event.occurred_at).toLocaleString()}</td>
                        <td className="py-3 pr-4">{event.actor}</td>
                        <td className="py-3 pr-4">{event.action}</td>
                        <td className="py-3"><Status positive={event.outcome.toUpperCase() === 'SUCCESS'}>{event.outcome}</Status></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="mt-4 text-sm text-ink-soft">No audit events have been recorded.</p>}
          </section>

          <section className="neo-card border border-dashed border-brand-300 bg-brand-50/30 p-5" aria-labelledby="security-demo-heading">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 id="security-demo-heading" className="font-bold text-ink">Example staff security configuration</h2>
                <p className="mt-1 text-xs text-amber-800">{DEMO_DATA_NOTICE} These examples do not reflect actual staff accounts or change security settings.</p>
              </div>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold uppercase text-amber-900">Demo</span>
            </div>
            <div className="mt-4 overflow-x-auto rounded-lg border border-ns-border bg-white">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead><tr className="border-b border-ns-border text-xs uppercase text-ink-faint"><th className="px-3 py-2">Example staff account</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">Example MFA state</th></tr></thead>
                <tbody>{DEMO_STAFF_SECURITY.map((staff) => (
                  <tr key={staff.name} className="border-b border-ns-border/70 last:border-0">
                    <td className="px-3 py-3">{staff.name}</td>
                    <td className="px-3 py-3">{staff.role}</td>
                    <td className="px-3 py-3"><Status>{staff.mfa}</Status></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {DEMO_ENCRYPTION_EXAMPLE.map((item) => (
                <div key={item.control} className="rounded-lg border border-ns-border bg-white p-3">
                  <p className="text-xs font-semibold uppercase text-ink-faint">{item.control}</p>
                  <p className="mt-1 text-sm text-ink-soft">{item.status}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="neo-card grid gap-4 p-5 md:grid-cols-2">
            <div>
              <h2 className="font-bold text-ink">Privacy notice</h2>
              <p className="mt-2"><Status>{security.privacy_notice.status.replace(/_/g, ' ')}</Status></p>
              <p className="mt-2 text-sm text-ink-soft">{security.privacy_notice.detail}</p>
            </div>
            <div>
              <h2 className="font-bold text-ink">Processing information</h2>
              <p className="mt-2 text-sm text-ink-soft">NeuroSync processes academic, attendance and learning-platform indicators to support staff review. Risk scores are indicators for human review, not diagnoses or automated decisions.</p>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
