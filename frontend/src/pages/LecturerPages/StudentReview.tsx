import { useEffect, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, CalendarCheck, Eye, LoaderCircle, Mail, MessageSquarePlus, Phone, Send } from 'lucide-react';
import NeoButton from '../../components/Buttons/NeoButton';
import ProgressComparisonCard from '../../components/Cards/ProgressComparisonCard';
import RiskExplanationPanel from '../../components/RiskExplanationPanel';
import BarChartCard from '../../components/Charts/BarChartCard';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { LmsStudentReview, LmsReferral } from '../../types';
import { riskBg } from '../../utils/helpers';
import { useToast } from '../../components/Toast';

type Tab = 'OVERVIEW' | 'ATTENDANCE' | 'SUBMISSIONS' | 'ASSESSMENTS' | 'QUIZZES' | 'LMS ENGAGEMENT' | 'RISK ANALYSIS' | 'INTERVENTIONS / REFERRALS';
type SubmissionFilter = 'ALL' | 'SUBMITTED' | 'LATE' | 'MISSING';

const tabs: Tab[] = ['OVERVIEW', 'ATTENDANCE', 'SUBMISSIONS', 'ASSESSMENTS', 'QUIZZES', 'LMS ENGAGEMENT', 'RISK ANALYSIS', 'INTERVENTIONS / REFERRALS'];

export default function StudentReview() {
  const { studentId = '' } = useParams();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { token } = useAuth();
  const { showToast } = useToast();
  const [review, setReview] = useState<LmsStudentReview | null>(null);
  const [tab, setTab] = useState<Tab>('OVERVIEW');
  const [submissionFilter, setSubmissionFilter] = useState<SubmissionFilter>('ALL');
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const isAdminProfile = location.pathname.startsWith('/admin/');
  const [referralOpen, setReferralOpen] = useState(!isAdminProfile && searchParams.get('refer') === '1');
  const [moduleId, setModuleId] = useState('');
  const [reason, setReason] = useState('');
  const [lecturerNotes, setLecturerNotes] = useState('');
  const [urgency, setUrgency] = useState<'STANDARD' | 'PRIORITY'>('STANDARD');
  const [savingReferral, setSavingReferral] = useState(false);
  const [notice, setNotice] = useState('');

  const continueMonitoring = async () => {
    if (!moduleId) return;
    if (!window.confirm('Continue monitoring this student without creating an intervention?')) return;
    setNotice('');
    setError('');
    try {
      await api.post(`/workflow/students/${studentId}/monitor?module_id=${moduleId}`, {}, token || undefined);
      setNotice('Continue monitoring recorded. No intervention was created.');
      showToast('Monitoring action recorded.');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not record monitoring action';
      setError(message);
      showToast(message, 'error');
    }
  };

  useEffect(() => {
    let active = true;
    api.get<LmsStudentReview>(`/workflow/students/${studentId}/review`, token || undefined)
      .then((data) => { if (active) { setReview(data); setModuleId(data.modules[0]?.module_id || ''); } })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  const submitReferral = async () => {
    if (!reason.trim()) return;
    setSavingReferral(true);
    setError('');
    try {
      const referral = await api.post<LmsReferral>('/workflow/referrals', {
        student_id: studentId,
        module_id: moduleId || null,
        reason,
        lecturer_notes: lecturerNotes || null,
        urgency
      }, token || undefined);
      setReview((current) => current ? { ...current, referrals: [referral, ...current.referrals] } : current);
      setReferralOpen(false);
      setReason('');
      setLecturerNotes('');
      setNotice(`Referral ${referral.referral_id} sent to the advisor queue.`);
      showToast('Referral sent to the advisor queue.');
      setTab('INTERVENTIONS / REFERRALS');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not create referral';
      setError(message);
      showToast(message, 'error');
    } finally {
      setSavingReferral(false);
    }
  };

  const recommendWellness = async () => {
    const studentMessage = window.prompt(
      'Add a supportive message inviting the student to speak with Student Wellness:',
      'Your university recommends speaking with a Student Wellness professional. You can book a confidential appointment through your recommendations.'
    );
    if (!studentMessage?.trim()) return;
    try {
      await api.post('/wellbeing/referrals', { student_id: studentId, student_message: studentMessage.trim() }, token || undefined);
      showToast('Student Wellness support recommendation recorded.');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not record the Wellness recommendation.';
      setError(message);
      showToast(message, 'error');
    }
  };

  if (loading) return <div className="flex items-center justify-center gap-2 py-16 text-sm text-ink-soft"><LoaderCircle className="animate-spin" />Loading authorised LMS profile…</div>;
  if (error && !review) return <div className="neo-card p-6" role="alert"><p className="text-ns-danger">{error}</p><Link className="mt-4 inline-block text-brand-800" to="/lecturer/students">Back to students</Link></div>;
  if (!review) return null;

  const { student, metrics } = review;
  const filteredSubmissions = review.submissions.filter((item) => submissionFilter === 'ALL' || item.status === submissionFilter);
  const selectedSubmission = review.submissions.find((item) => item.submission_id === selectedSubmissionId) || null;
  const trendRows = review.attendance.reduce<Record<string, { present: number; total: number }>>((all, row) => {
    const month = row.date.slice(0, 7);
    all[month] ||= { present: 0, total: 0 };
    all[month].total += 1;
    if (row.status === 'PRESENT' || row.status === 'LATE') all[month].present += 1;
    return all;
  }, {});
  const attendanceTrend = Object.entries(trendRows).sort(([a], [b]) => a.localeCompare(b)).map(([name, row]) => ({ name, value: Math.round(row.present / row.total * 100) }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
            <Link to={isAdminProfile ? '/admin/users' : '/lecturer/students'} className="inline-flex items-center gap-2 text-sm font-medium text-brand-800 hover:text-brand-700"><ArrowLeft size={16} /> {isAdminProfile ? 'User management' : 'Students'}</Link>
            <span className="text-xs text-ns-text-muted">{isAdminProfile ? 'Administrator read-only profile' : 'Synthetic Mock LMS record'}</span>
      </div>
      <section className="neo-card p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase text-ns-text-muted">{student.student_id}</p>
            <h1 className="mt-1 text-2xl font-bold text-ns-text-primary">{student.name}</h1>
            <p className="mt-1 text-sm text-ns-text-secondary">{student.programme} · {student.faculty} · Year {student.year_of_study} · <a className="text-brand-800" href={`mailto:${student.institutional_email}`}>{student.institutional_email}</a></p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a className="neo-btn inline-flex items-center gap-1.5 px-3 py-2 text-xs" href={`mailto:${student.institutional_email}`}><Mail size={14} />Email student</a>
              <button type="button" className="neo-btn inline-flex items-center gap-1.5 px-3 py-2 text-xs" onClick={() => showToast('No phone number is recorded for this student.', 'info')}><Phone size={14} />Call student</button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">{review.modules.map((module) => <span key={module.module_id} className="neo-chip bg-brand-50 text-brand-800">{module.module_code}</span>)}</div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`neo-chip ${riskBg(review.risk.risk_level)}`}>Risk: {review.risk.risk_level} · {review.risk.risk_score}%</span>
            {!isAdminProfile && <><NeoButton variant="secondary" onClick={continueMonitoring}><Eye size={15} className="mr-1.5 inline" />Continue monitoring</NeoButton>
            <NeoButton variant="secondary" onClick={() => setReferralOpen(true)}><MessageSquarePlus size={16} className="mr-1.5 inline" />Refer to advisor</NeoButton>
            <NeoButton variant="secondary" onClick={() => void recommendWellness()}><MessageSquarePlus size={16} className="mr-1.5 inline" />Recommend Wellness</NeoButton></>}
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 lg:grid-cols-5 gap-3">
          <Metric label="Academic average" value={`${metrics.academic_average}%`} />
          <Metric label="Attendance" value={`${metrics.attendance}%`} />
          <Metric label="Submission rate" value={`${metrics.submission_rate}%`} />
          <Metric label="Quiz average" value={`${metrics.quiz_average}%`} />
          <Metric label="LMS engagement" value={`${metrics.engagement_score}/100`} />
        </div>
        <div className="mt-3 rounded-lg border border-ns-border bg-ns-surface-secondary p-3">
          <p className="text-xs text-ns-text-muted">Mood / wellbeing</p>
          <p className="mt-1 text-sm font-semibold text-ns-text-primary">Not recorded in the current dataset</p>
        </div>
      </section>

      <RiskExplanationPanel risk={review.risk} metrics={review.metrics} />

      {notice && <div role="status" className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-ns-success">{notice}</div>}
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-ns-danger">{error}</div>}

      <div className="border-b border-ns-border overflow-x-auto">
        <div className="flex min-w-max gap-1" role="tablist" aria-label="Student academic review">
          {tabs.map((item) => <button key={item} role="tab" aria-selected={tab === item} onClick={() => setTab(item)} className={`px-3 py-2.5 text-xs font-semibold whitespace-nowrap border-b-2 ${tab === item ? 'border-brand-700 text-brand-800' : 'border-transparent text-ns-text-muted hover:text-ns-text-primary'}`}>{item}</button>)}
        </div>
      </div>

      {tab === 'OVERVIEW' && <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <BarChartCard title="Attendance trend" subtitle="Present or late by month" data={attendanceTrend} color="var(--ns-primary-dark)" />
        <section className="neo-card p-5"><h2 className="font-semibold text-ns-text-primary">Current evidence</h2><ul className="mt-3 space-y-2">{review.risk.evidence.map((line) => <li key={line} className="flex gap-2 text-sm text-ns-text-secondary"><span className="text-brand-700">•</span>{line}</li>)}</ul></section>
        <section className="neo-card p-5 xl:col-span-2"><h2 className="font-semibold text-ns-text-primary">Recent academic activity</h2><div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3"><Metric label="Late submissions" value={metrics.late_submissions} /><Metric label="Missing submissions" value={metrics.missing_submissions} /><Metric label="Logins this week" value={metrics.logins_this_week} /><Metric label="Last login" value={metrics.last_login ? new Date(metrics.last_login).toLocaleDateString() : 'No login recorded'} /></div></section>
      </div>}

      {tab === 'ATTENDANCE' && <div className="space-y-5"><div className="grid grid-cols-2 lg:grid-cols-5 gap-3"><Metric label="Overall" value={`${metrics.attendance}%`} /><Metric label="Last 30 days" value={`${metrics.attendance_30d}%`} /><Metric label="Last 7 days" value={`${metrics.attendance_7d}%`} /><Metric label="Classes attended" value={metrics.classes_attended} /><Metric label="Missed / late" value={`${metrics.classes_missed} / ${metrics.late_arrivals}`} /></div><BarChartCard title="Attendance trend" subtitle="Present or late by month" data={attendanceTrend} color="var(--ns-primary-dark)" /><DataTable headers={['Date', 'Session', 'Module', 'Status']} rows={review.attendance.map((row) => [row.date, row.session, row.module_id, row.status])} /></div>}

      {tab === 'SUBMISSIONS' && <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3"><Metric label="Submission rate" value={`${metrics.submission_rate}%`} /><Metric label="Late submissions" value={metrics.late_submissions} /><Metric label="Missing submissions" value={metrics.missing_submissions} /></div>
        <div className="flex flex-wrap gap-2">{(['ALL', 'SUBMITTED', 'LATE', 'MISSING'] as const).map((filter) => <button key={filter} onClick={() => setSubmissionFilter(filter)} className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${submissionFilter === filter ? 'border-brand-700 bg-brand-700 text-white' : 'border-ns-border bg-white text-ns-text-secondary'}`}>{filter}</button>)}</div>
        <div className="neo-card overflow-x-auto"><table className="ns-table min-w-[850px]"><thead><tr>{['Assessment', 'Module', 'Type', 'Due', 'Submitted', 'Status', 'Mark', 'Weight'].map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{filteredSubmissions.map((row) => <tr key={row.submission_id}><td><button className="font-semibold text-brand-800 hover:underline" onClick={() => setSelectedSubmissionId(row.submission_id)}>{row.assessment}</button></td><td>{row.module_code}</td><td>{row.type}</td><td>{row.due_date}</td><td>{row.submitted_at ? new Date(row.submitted_at).toLocaleDateString() : '—'}</td><td><span className={`neo-chip ${row.status === 'MISSING' ? 'bg-red-50 text-ns-danger' : row.status === 'LATE' ? 'bg-amber-50 text-ns-warning' : 'bg-ns-surface-secondary text-ns-text-secondary'}`}>{row.status}</span></td><td>{row.mark == null ? '—' : `${row.mark}%`}</td><td>{row.weight}%</td></tr>)}</tbody></table></div>
        {selectedSubmission && <section className="neo-card p-5" aria-labelledby="submission-detail-title"><div className="flex items-start justify-between gap-3"><div><h2 id="submission-detail-title" className="font-semibold">{selectedSubmission.assessment}</h2><p className="mt-1 text-xs text-ns-text-muted">Synthetic Mock LMS metadata. No student assignment file is stored.</p></div><button className="text-sm text-brand-800" onClick={() => setSelectedSubmissionId(null)}>Close</button></div><dl className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3"><Detail label="Module" value={`${selectedSubmission.module_code} · ${selectedSubmission.module_id}`} /><Detail label="Due date" value={selectedSubmission.due_date} /><Detail label="Submission status" value={selectedSubmission.status} /><Detail label="Submission timestamp" value={selectedSubmission.submitted_at ? new Date(selectedSubmission.submitted_at).toLocaleString() : 'Not submitted'} /><Detail label="Mark" value={selectedSubmission.mark == null ? '—' : `${selectedSubmission.mark}%`} /><Detail label="Weight" value={`${selectedSubmission.weight}%`} /><Detail label="Feedback" value={selectedSubmission.feedback || 'No feedback recorded'} /></dl></section>}
      </div>}

      {tab === 'ASSESSMENTS' && <DataTable headers={['Assessment', 'Type', 'Module', 'Due date', 'Weight', 'Mark', 'Status']} rows={review.assessments.map((row) => [row.assessment, row.type, row.module_code, row.due_date, `${row.weight}%`, `${row.mark}%`, row.status])} />}
      {tab === 'QUIZZES' && <div className="space-y-4"><div className="grid grid-cols-2 gap-3"><Metric label="Quiz average" value={`${metrics.quiz_average}%`} /><Metric label="Completion rate" value={`${metrics.quiz_completion_rate}%`} /></div><DataTable headers={['Quiz', 'Module', 'Attempt', 'Score', 'Completed', 'Duration']} rows={review.quizzes.map((row) => [row.quiz, row.module_code, row.attempt, `${row.percentage}%`, row.completed_at ? new Date(row.completed_at).toLocaleString() : 'In progress', `${row.duration} min`])} /></div>}

      {tab === 'LMS ENGAGEMENT' && <div className="grid grid-cols-2 lg:grid-cols-4 gap-3"><Metric label="Last login" value={metrics.last_login ? new Date(metrics.last_login).toLocaleDateString() : 'Not recorded'} /><Metric label="Days since login" value={metrics.days_since_last_login ?? '—'} /><Metric label="Logins this week" value={metrics.logins_this_week} /><Metric label="Resources viewed" value={metrics.resources_viewed} /><Metric label="Downloads" value={metrics.resources_downloaded} /><Metric label="Assessment pages" value={metrics.assessment_pages_viewed} /><Metric label="Quiz activity" value={metrics.quiz_activity} /><Metric label="Discussion activity" value={metrics.discussion_activity} /></div>}

      {tab === 'RISK ANALYSIS' && <section className="neo-card p-5"><div className="flex items-center gap-3"><AlertTriangle className="text-brand-800" /><div><h2 className="font-semibold">{review.risk.risk_level} risk · {review.risk.risk_score}%</h2><p className="text-xs text-ns-text-muted">Calculated from current Mock LMS indicators; staff retain decision authority.</p></div></div><h3 className="mt-5 text-sm font-semibold">Risk trajectory: {review.risk.trajectory.replace(/_/g, ' ')}</h3><ul className="mt-2 space-y-2">{review.risk.trajectory_evidence.length ? review.risk.trajectory_evidence.map((line) => <li className="text-sm text-ns-text-secondary" key={line}>• {line}</li>) : <li className="text-sm text-ns-text-secondary">Available recent indicators do not show a sustained directional change.</li>}</ul><h3 className="mt-5 text-sm font-semibold">Why NeuroSync flagged this student</h3><ul className="mt-2 space-y-2">{review.risk.evidence.map((line) => <li className="text-sm text-ns-text-secondary" key={line}>• {line}</li>)}</ul></section>}

      {tab === 'INTERVENTIONS / REFERRALS' && <div className="space-y-4"><div className="flex items-center justify-between"><h2 className="font-semibold">Referral and intervention history</h2><NeoButton onClick={() => setReferralOpen(true)}><MessageSquarePlus size={16} className="mr-1.5 inline" />Refer to advisor</NeoButton></div>{review.referrals.length === 0 ? <section className="neo-card p-6 text-sm text-ns-text-muted">No referrals recorded.</section> : review.referrals.map((referral) => <section className="neo-card p-5" key={referral.referral_id}><div className="flex flex-wrap justify-between gap-2"><strong>{referral.referral_id}</strong><span className="neo-chip bg-brand-50 text-brand-800">{referral.status}</span></div><p className="mt-2 text-sm">{referral.reason}</p><p className="mt-1 text-xs text-ns-text-muted">{referral.urgency} · {new Date(referral.created_at).toLocaleString()}</p></section>)}{review.interventions.map((item) => <section className="neo-card p-5" key={item.intervention_id}><div className="flex justify-between gap-2"><strong>{item.strategy}</strong><span className="neo-chip bg-brand-50 text-brand-800">{item.status}</span></div><p className="mt-2 text-sm text-ns-text-secondary">{item.reason}</p></section>)}</div>}

      {tab === 'INTERVENTIONS / REFERRALS' && review.intervention_comparison && <ProgressComparisonCard comparison={review.intervention_comparison} title="Academic change since referral" />}

      {tab === 'INTERVENTIONS / REFERRALS' && review.timeline.length > 0 && <section className="neo-card p-5"><h2 className="font-semibold">Shared case timeline</h2><ol className="mt-4 space-y-3">{review.timeline.map((event, index) => <li key={`${event.occurred_at}-${index}`} className="border-l-2 border-brand-300 pl-4"><p className="text-xs text-ns-text-muted">{new Date(event.occurred_at).toLocaleString()}</p><p className="text-sm">{event.summary}</p></li>)}</ol></section>}

      {referralOpen && <div className="fixed inset-0 z-50 flex items-center justify-center p-4"><button aria-label="Close referral form" className="absolute inset-0 bg-ns-black/40" onClick={() => setReferralOpen(false)} /><section role="dialog" aria-modal="true" aria-labelledby="referral-title" className="relative max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-lg border border-ns-border bg-white p-5 shadow-xl"><h2 id="referral-title" className="text-lg font-semibold">Refer to academic advisor</h2><p className="mt-1 text-xs text-ns-text-muted">The advisor receives LMS evidence and your notes. AI does not make the referral decision.</p><div className="mt-4 space-y-4"><div><label className="block text-sm font-medium">Student</label><input className="neo-input mt-1" value={`${student.student_id} · ${student.name}`} readOnly /></div><div><label className="block text-sm font-medium">Module</label><select className="neo-input mt-1" value={moduleId} onChange={(event) => setModuleId(event.target.value)}>{review.modules.map((module) => <option value={module.module_id} key={module.module_id}>{module.module_code} · {module.module_name}</option>)}</select></div><div><label className="block text-sm font-medium">Current risk</label><input className="neo-input mt-1" value={`${review.risk.risk_level} · ${review.risk.risk_score}%`} readOnly /></div><div><p className="text-sm font-medium">Supporting factors</p><ul className="mt-1 text-sm text-ns-text-secondary">{review.risk.evidence.map((item) => <li key={item}>• {item}</li>)}</ul></div><div><label className="block text-sm font-medium">Referral reason</label><textarea className="neo-input mt-1" value={reason} onChange={(event) => setReason(event.target.value)} rows={3} maxLength={2000} /></div><div><label className="block text-sm font-medium">Lecturer notes (shared)</label><textarea className="neo-input mt-1" value={lecturerNotes} onChange={(event) => setLecturerNotes(event.target.value)} rows={3} maxLength={4000} /></div><div><label className="block text-sm font-medium">Urgency</label><select className="neo-input mt-1" value={urgency} onChange={(event) => setUrgency(event.target.value as 'STANDARD' | 'PRIORITY')}><option value="STANDARD">Standard</option><option value="PRIORITY">Priority</option></select></div></div><div className="mt-5 flex justify-end gap-2"><NeoButton variant="secondary" onClick={() => setReferralOpen(false)}>Cancel</NeoButton><NeoButton onClick={submitReferral} loading={savingReferral}><Send size={15} className="mr-1.5 inline" />Submit referral</NeoButton></div></section></div>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3"><p className="text-xs text-ns-text-muted">{label}</p><p className="mt-1 text-lg font-semibold text-brand-800">{value}</p></div>;
}

function Detail({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3"><dt className="text-xs text-ns-text-muted">{label}</dt><dd className="mt-1 text-sm font-medium text-ns-text-primary">{value}</dd></div>;
}

function DataTable({ headers, rows }: { headers: string[]; rows: (string | number)[][] }) {
  return <div className="neo-card overflow-x-auto"><table className="ns-table min-w-[720px]"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody></table></div>;
}
