import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import StatCard from '../../components/Cards/StatCard';
import DashboardHero from '../../components/DashboardHero';
import LoadingState from '../../components/LoadingState';
import WeeklyBriefing from '../../components/WeeklyBriefing';
import ActionQueue from '../../components/ActionQueue';
import SupportRequestQueue from '../../components/SupportRequestQueue';
import ImportedDemoDatasetSection, { type ImportedDemoDataset } from '../../components/ImportedDemoDataset';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { lecturerDashboard } from '../../services/mockData';
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
  const demoStudents = lecturerDashboard.students;
  const demoHighRiskCount = demoStudents.filter((student) => student.risk_level === 'HIGH').length;
  const demoReviewCount = demoStudents.filter((student) => student.risk_level !== 'LOW').length;
  return (
    <div className="space-y-6">
      <DashboardHero
        icon={<Sparkles size={42} strokeWidth={1.5} />}
      />

      <section aria-labelledby="native-lms-workflow-title">
        <div className="mb-3">
          <h2 id="native-lms-workflow-title" className="font-semibold text-ns-text-primary">Live LMS workflow</h2>
          <p className="mt-1 text-xs text-ns-text-secondary">These are live backend workflow counts. Sample students are displayed separately below and do not create referrals or cases.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard title="New referrals" value={summary.new_referrals} />
          <StatCard title="Assigned students" value={summary.assigned_students} />
          <StatCard title="Students to contact" value={summary.students_to_contact} />
          <StatCard title="Awaiting response" value={summary.awaiting_response} />
          <StatCard title="Meetings scheduled" value={summary.meetings_scheduled} />
          <StatCard title="Active interventions" value={summary.active_interventions} />
          <StatCard title="Follow-ups due" value={summary.follow_ups_due} />
          <StatCard title="Resolved cases" value={summary.resolved_cases} />
        </div>
      </section>

      <section className="neo-card border border-dashed border-brand-300 p-5" aria-labelledby="advisor-demo-cohort-title">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="advisor-demo-cohort-title" className="font-bold text-ns-text-primary">Demo cohort · shared with Lecturer view</h2>
            <p className="mt-1 text-xs text-amber-800">Illustrative records from the shared frontend demo student list. These do not represent live referrals, and no advisor actions are available for them.</p>
          </div>
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold uppercase text-amber-900">Demo data</span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:max-w-md">
          <StatCard title="Demo students for review" value={demoReviewCount} />
          <StatCard title="Demo high-risk students" value={demoHighRiskCount} />
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="ns-table min-w-[760px]">
            <caption className="sr-only">Sample students shared with the lecturer demo roster</caption>
            <thead><tr><th>Student</th><th>Student number</th><th>Module</th><th>Risk indicator</th><th>Average mark</th><th>Attendance</th><th>Evidence from Lecturer view</th></tr></thead>
            <tbody>{demoStudents.map((student) => (
              <tr key={student.id}>
                <td>{student.name}</td>
                <td>{student.student_number}</td>
                <td>{student.module}</td>
                <td><span className={`neo-chip ${riskBg(student.risk_level)}`}>{student.risk_level}</span></td>
                <td>{student.average_mark}%</td>
                <td>{student.attendance}%</td>
                <td className="max-w-[280px] whitespace-normal">{student.ai_explanation}</td>
              </tr>
            ))}</tbody>
          </table>
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
