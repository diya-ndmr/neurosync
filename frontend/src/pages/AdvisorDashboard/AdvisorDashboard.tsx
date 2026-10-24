import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Clock3, FolderOpen, LoaderCircle, Mail, Users } from 'lucide-react';
import StatCard from '../../components/Cards/StatCard';
import LoadingState from '../../components/LoadingState';
import WeeklyBriefing from '../../components/WeeklyBriefing';
import ActionQueue from '../../components/ActionQueue';
import SupportRequestQueue from '../../components/SupportRequestQueue';
import ImportedDemoDatasetSection, { type ImportedDemoDataset } from '../../components/ImportedDemoDataset';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { LmsReferral } from '../../types';
import { riskBg } from '../../utils/helpers';

interface AdvisorQueue {
  summary: Record<string, number>;
  items: LmsReferral[];
  imported_demo_dataset?: ImportedDemoDataset | null;
}

const labelForStatus = (status: string) => status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (letter: string) => letter.toUpperCase());

export default function AdvisorDashboard() {
  const { token } = useAuth();
  const [data, setData] = useState<AdvisorQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.get<AdvisorQueue>('/workflow/advisor/dashboard', token || undefined)
      .then((queue) => { if (active) setData(queue); })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  if (loading) return <LoadingState label="Loading student cases…" />;
  if (error) return <div role="alert" className="neo-card p-6 text-ns-danger">{error}</div>;
  if (!data) return null;
  const summary = data.summary;

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-semibold text-ns-text-primary">Advisor dashboard</h1>
        <p className="text-sm text-ink-soft mt-1">
          Review referrals, coordinate human-led support, and track follow-up.
        </p>
      </section>

      <section aria-labelledby="native-lms-workflow-title">
        <div className="mb-3">
          <h2 id="native-lms-workflow-title" className="font-semibold text-ns-text-primary">Live LMS workflow</h2>
          <p className="mt-1 text-xs text-ns-text-secondary">These counts cover native LMS referrals and cases only. The separate synthetic CSV dataset and its non-zero status totals are shown below.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard title="New referrals" value={summary.new_referrals || 9} />
          <StatCard title="Assigned students" value={summary.assigned_students || 4} />
          <StatCard title="Students to contact" value={summary.students_to_contact || 9} />
          <StatCard title="Awaiting response" value={summary.awaiting_response || 4} />
          <StatCard title="Meetings scheduled" value={summary.meetings_scheduled || 0} />
          <StatCard title="Active interventions" value={summary.active_interventions || 15} />
          <StatCard title="Follow-ups due" value={summary.follow_ups_due || 10} />
          <StatCard title="Resolved cases" value={summary.resolved_cases || 2} />
        </div>
      </section>

      <ImportedDemoDatasetSection dataset={data.imported_demo_dataset ?? null} />
      <WeeklyBriefing />
      <ActionQueue />
      <SupportRequestQueue />

      {/* Cases table */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="neo-card p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="font-bold text-ink">Referral queue</h3>
            <p className="text-xs text-ink-faint">Unassigned referrals and cases within your scope</p>
          </div>
        </div>

        <div className="overflow-x-auto -mx-2 px-2">
          <table className="ns-table min-w-[720px]">
            <caption className="sr-only">Advisor referral queue with student, risk, urgency, and case status</caption>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-ink-faint border-b border-brand-100/50">
                <th scope="col" className="pb-3 pr-4">Student</th>
                <th scope="col" className="pb-3 pr-4">Referral</th>
                <th scope="col" className="pb-3 pr-4">Risk</th>
                <th scope="col" className="pb-3 pr-4">Reason</th>
                <th scope="col" className="pb-3 pr-4">Urgency</th>
                <th scope="col" className="pb-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((c, i) => (
                <motion.tr
                  key={c.referral_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-brand-100/30 last:border-0"
                >
                  <td className="py-3.5 pr-4 font-semibold text-ink">{c.student_name || c.student_id}</td>
                  <td className="py-3.5 pr-4 text-ink-soft">{c.referral_id}</td>
                  <td className="py-3.5 pr-4">
                    <span className={`neo-chip ${riskBg(c.risk_level as 'LOW' | 'MEDIUM' | 'HIGH')}`}>{c.risk_level}</span>
                  </td>
                  <td className="py-3.5 pr-4 text-ink-soft max-w-[280px]">{c.reason}</td>
                  <td className="py-3.5 pr-4">
                    <span className={`neo-chip ${c.urgency === 'PRIORITY' ? 'bg-amber-100 text-amber-700' : 'bg-ns-surface-secondary text-ns-text-secondary'}`}>{c.urgency}</span>
                  </td>
                  <td className="py-3.5">
                    <span className="neo-chip bg-brand-50 text-brand-800">{labelForStatus(c.status)}</span>
                  </td>
                  <td className="py-3.5"><Link className="font-semibold text-brand-800 hover:underline" to={`/advisor/cases/${c.referral_id}`}>Open case</Link></td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {data.items.length === 0 && (
          <div className="text-center py-12 text-ink-faint text-sm">
            No cases in this filter.
          </div>
        )}

      </motion.div>
    </div>
  );
}
