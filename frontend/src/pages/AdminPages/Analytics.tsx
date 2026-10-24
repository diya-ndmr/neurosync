import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import StatCard from '../../components/Cards/StatCard';
import BarChartCard from '../../components/Charts/BarChartCard';
import LineChartCard from '../../components/Charts/LineChartCard';
import PieChartCard from '../../components/Charts/PieChartCard';
import RiskLatticeDiagram from '../../components/Charts/RiskLatticeDiagram';
import LoadingState from '../../components/LoadingState';
import { useApiData } from '../../hooks/useApiData';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { fetchAdminAnalytics } from '../../services/liveData';
import { useToast } from '../../components/Toast';

interface RecoveringStudent {
  student_id: string;
  student_name: string;
  programme: string;
  year_level: number;
  risk_history: { risk_level: 'HIGH' | 'MEDIUM' | 'LOW'; risk_score: number; model_version: string; created_at: string | null }[];
  latest_updated_at: string | null;
}

interface RadarInsight {
  category: 'EMERGING_RISK' | 'WATCH' | 'IMPROVING' | 'DATA_ISSUE';
  title: string;
  student_id: string;
  student_name: string;
  programme: string;
  observed_at: string | null;
  evidence: string[];
  record_ids: string[];
}

interface IntelligenceAnswer {
  supported: boolean;
  answer: string;
  items: RadarInsight[];
}

interface WorkbookRow { sheet: string; [key: string]: unknown }

export default function Analytics() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const { data, loading, error } = useApiData(fetchAdminAnalytics);
  const [recovering, setRecovering] = useState<RecoveringStudent[]>([]);
  const [recoveryLoading, setRecoveryLoading] = useState(true);
  const [recoveryError, setRecoveryError] = useState('');
  const [radar, setRadar] = useState<RadarInsight[]>([]);
  const [radarLoading, setRadarLoading] = useState(true);
  const [radarError, setRadarError] = useState('');
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState('');
  const [answer, setAnswer] = useState<IntelligenceAnswer | null>(null);
  const [workbookSheet, setWorkbookSheet] = useState('Students At Risk');
  const [workbookRows, setWorkbookRows] = useState<WorkbookRow[]>([]);
  const [workbookLoading, setWorkbookLoading] = useState(false);
  const [workbookError, setWorkbookError] = useState('');
  const weeklySummary = workbookSheet === 'Weekly Intelligence' ? workbookRows[0] : undefined;
  const weeklyMetrics = weeklySummary ? [
    { label: 'Report week', value: `${weeklySummary.report_week_start} – ${weeklySummary.report_week_end}` },
    { label: 'Students included', value: String(workbookRows.length) },
    { label: 'Cohort retention', value: `${weeklySummary.cohort_retention_rate_pct}%` },
    { label: 'Cohort logins (7d)', value: String(weeklySummary.cohort_logins_this_week) },
    { label: 'New referrals (7d)', value: String(weeklySummary.cohort_new_referrals_7d) },
    { label: 'Priority referrals (7d)', value: String(weeklySummary.cohort_priority_referrals_7d) },
    { label: 'High-risk referrals (7d)', value: String(weeklySummary.cohort_high_risk_referrals_7d) },
  ] : [];

  const askNeuroSync = async (prompt = question) => {
    if (!token || !prompt.trim()) return;
    setAsking(true);
    setAskError('');
    setAnswer(null);
    try {
      const result = await api.post<IntelligenceAnswer>('/admin/ask', { question: prompt.trim() }, token);
      setAnswer(result);
      showToast('Answer ready from recorded university data.', 'success');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Question could not be answered.';
      setAskError(message);
      showToast(message, 'error');
    } finally {
      setAsking(false);
    }
  };

  useEffect(() => {
    if (!token) {
      setRecoveryLoading(false);
      return;
    }
    let active = true;
    api.get<{ items: RecoveringStudent[] }>('/admin/recovering-students', token)
      .then((result) => { if (active) setRecovering(result.items); })
      .catch((requestError: Error) => { if (active) setRecoveryError(requestError.message); })
      .finally(() => { if (active) setRecoveryLoading(false); });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    setWorkbookRows([]);
    setWorkbookError('');
    setWorkbookLoading(true);
    const limit = workbookSheet === 'Weekly Intelligence' ? 500 : 12;
    api.get<{ items: WorkbookRow[] }>(`/admin/workbook-intelligence?sheet=${encodeURIComponent(workbookSheet)}&limit=${limit}`, token)
      .then((result) => { if (active) setWorkbookRows(result.items); })
      .catch((requestError: Error) => { if (active) setWorkbookError(requestError.message); })
      .finally(() => { if (active) setWorkbookLoading(false); });
    return () => { active = false; };
  }, [token, workbookSheet]);

  useEffect(() => {
    if (!token) {
      setRadarLoading(false);
      return;
    }
    let active = true;
    api.get<{ items: RadarInsight[] }>('/admin/radar', token)
      .then((result) => { if (active) setRadar(result.items); })
      .catch((requestError: Error) => { if (active) setRadarError(requestError.message); })
      .finally(() => { if (active) setRadarLoading(false); });
    return () => { active = false; };
  }, [token]);

  if (loading) return <LoadingState label="Loading university overview…" />;
  if (error || !data) {
    return <section className="neo-card p-6 text-sm text-ns-danger">{error ?? 'Analytics unavailable.'}</section>;
  }
  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-semibold text-ink">University overview</h1>
        <p className="text-sm text-ink-soft">Progress, attendance, support needs, and outcomes</p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <StatCard title="Total Students" value={data.total_students.toLocaleString()} />
        <StatCard title="High Risk" value={data.high_risk_students.toLocaleString()} />
        <StatCard title="Avg Performance" value={data.average_performance == null ? 'No data' : `${data.average_performance}%`} />
        <StatCard title="Retention Rate" value={data.retention_rate == null ? 'No data' : `${data.retention_rate}%`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <PieChartCard
          title="Risk Distribution"
          subtitle="All students"
          data={data.risk_distribution}
          index={0}
        />
        <LineChartCard
          title="Attendance Trend"
          subtitle="Institution average"
          data={data.attendance_trend.map((a) => ({ name: a.month, value: a.percentage }))}
          index={1}
        />
        <LineChartCard
          title="Performance Trend"
          subtitle="Institution average mark"
          data={data.performance_trend.map((p) => ({ name: p.month, value: p.average }))}
          index={2}
        />
      </div>

      <RiskLatticeDiagram data={data.risk_distribution} />

      <section className="neo-card overflow-hidden" aria-labelledby="workbook-highlights-heading">
        <div className="border-b border-ns-divider px-5 py-4">
          <h2 id="workbook-highlights-heading" className="font-bold text-ink">Workbook highlights</h2>
          <p className="mt-1 text-sm text-ink-soft">Imported CSV records and additional university data, including the latest weekly intelligence report.</p>
        </div>
        <div className="flex flex-wrap gap-2 border-b border-ns-divider px-5 py-3">
          {['Students At Risk', 'Top Students', 'Students Recovering', 'AI Recommendations', 'Lecturer Overview', 'Advisor Overview', 'Weekly Intelligence', 'audit_logs', 'ml_features', 'study_activity', 'support_requests', 'students', 'user_accounts', 'wellbeing'].map((sheet) => <button key={sheet} type="button" onClick={() => setWorkbookSheet(sheet)} className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${workbookSheet === sheet ? 'border-brand-700 bg-brand-700 text-white' : 'border-ns-border text-ns-text-secondary'}`}>{sheet.replace('AI Recommendations', 'Recommendations').replace(/_/g, ' ')}</button>)}
        </div>
        {weeklySummary && !workbookLoading && !workbookError && <div className="grid grid-cols-2 gap-3 px-5 pt-4 sm:grid-cols-3 xl:grid-cols-4">{weeklyMetrics.map((metric) => <div key={metric.label} className="rounded-lg border border-ns-divider p-3"><p className="text-xs text-ns-text-muted">{metric.label}</p><p className="mt-1 text-sm font-semibold text-ns-text-primary">{metric.value}</p></div>)}</div>}
        {weeklySummary && !workbookLoading && !workbookError && <p className="px-5 pt-3 text-xs text-ns-text-muted">Source: {String(weeklySummary.data_origin ?? 'Not specified')}</p>}
        {workbookLoading ? <p className="px-5 py-6 text-sm text-ns-text-muted">Loading workbook section…</p> : workbookError ? <p role="alert" className="px-5 py-6 text-sm text-ns-danger">Workbook section unavailable: {workbookError}</p> : workbookRows.length === 0 ? <p className="px-5 py-6 text-sm text-ns-text-muted">No records in this section.</p> : <div className="overflow-x-auto"><table className="ns-table min-w-[760px]"><thead><tr>{(workbookSheet === 'Weekly Intelligence' ? ['student_id', 'risk_band', 'report_week_start', 'logins_this_week', 'attendance_7d_pct', 'attendance_30d_pct', 'new_referrals_7d'] : Object.keys(workbookRows[0]).filter((key) => key !== 'sheet').slice(0, 6)).map((key) => <th key={key}>{key.replace(/_/g, ' ')}</th>)}</tr></thead><tbody>{workbookRows.map((row, index) => <tr key={`${workbookSheet}-${index}`}>{(workbookSheet === 'Weekly Intelligence' ? ['student_id', 'risk_band', 'report_week_start', 'logins_this_week', 'attendance_7d_pct', 'attendance_30d_pct', 'new_referrals_7d'] : Object.keys(row).filter((key) => key !== 'sheet').slice(0, 6)).map((key) => <td key={key}>{String(row[key] ?? '—')}</td>)}</tr>)}</tbody></table></div>}
      </section>

      <BarChartCard
        title="Programme Comparison"
        subtitle="Average performance by programme"
        data={data.programme_comparison.map((p) => ({
          name: p.programme,
          value: p.average
        }))}
        index={0}
      />

      <section className="neo-card p-5" aria-labelledby="ask-neurosync-heading">
        <div className="border-b border-ns-divider pb-4">
          <h2 id="ask-neurosync-heading" className="font-bold text-ink">Ask NeuroSync</h2>
          <p className="mt-1 text-sm text-ink-soft">Answers use recorded risk history and prediction coverage only.</p>
        </div>
        <form className="mt-4 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => { event.preventDefault(); void askNeuroSync(); }}>
          <input
            aria-label="Ask NeuroSync a question"
            className="neo-input min-w-0 flex-1"
            maxLength={500}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Which students require attention?"
          />
          <button type="submit" disabled={asking || !question.trim()} className="neo-btn inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm">
            {asking ? 'Checking records…' : 'Ask'}
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2" aria-label="Suggested questions">
          {['Which students require attention?', 'Who is recovering?', 'Show data issues'].map((suggestion) => <button
            key={suggestion}
            type="button"
            disabled={asking}
            onClick={() => { setQuestion(suggestion); void askNeuroSync(suggestion); }}
            className="rounded-md border border-ns-border px-3 py-1.5 text-xs text-ns-text-secondary transition-colors hover:border-brand-500 hover:text-brand-800 disabled:opacity-50"
          >{suggestion}</button>)}
        </div>
        {askError && <p role="alert" className="mt-4 text-sm text-ns-danger">{askError}</p>}
        {answer && <div className="mt-4 rounded-md border border-ns-border bg-ns-surface-secondary/60 p-4" aria-live="polite">
          <p className="text-sm font-semibold text-ns-text-primary">{answer.answer}</p>
          {answer.items.length > 0 && <ul className="mt-3 divide-y divide-ns-divider">{answer.items.slice(0, 20).map((item, index) => <li key={`${item.category}-${item.student_id}-${index}`} className="py-3 first:pt-0 last:pb-0">
            <p className="text-xs font-semibold uppercase text-brand-800">{item.category.replace(/_/g, ' ')}</p>
            <p className="mt-1 text-sm font-medium text-ns-text-primary">{item.student_name} · {item.student_id}</p>
            <ul className="mt-1">{item.evidence.map((line) => <li key={line} className="text-sm text-ns-text-secondary">• {line}</li>)}</ul>
          </li>)}</ul>}
          {!answer.supported && <p className="mt-2 text-xs text-ns-text-muted">Try one of the suggested questions above.</p>}
        </div>}
      </section>

      <section className="neo-card overflow-hidden" aria-labelledby="radar-heading">
        <div className="border-b border-ns-divider px-5 py-4">
          <h2 id="radar-heading" className="font-bold text-ink">NeuroSync Radar</h2>
          <p className="mt-1 text-sm text-ink-soft">Signals from recorded risk history. Review supporting evidence before acting.</p>
        </div>
        {radarLoading ? <p className="px-5 py-6 text-sm text-ink-soft">Loading institutional signals…</p>
          : radarError ? <p role="alert" className="px-5 py-6 text-sm text-ns-danger">Radar unavailable: {radarError}</p>
            : radar.length === 0 ? <p className="px-5 py-6 text-sm text-ink-soft">No signals found in the available records.</p>
              : <ul className="divide-y divide-ns-divider">
                {radar.map((insight, index) => <li key={`${insight.category}-${insight.student_id}-${index}`} className="px-5 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase text-brand-800">{insight.category.replace(/_/g, ' ')}</p>
                      <h3 className="mt-1 font-semibold text-ns-text-primary">{insight.title}</h3>
                      <p className="mt-1 text-sm text-ns-text-secondary">{insight.student_name} · {insight.student_id} · {insight.programme}</p>
                    </div>
                    <time className="text-xs text-ns-text-muted">{insight.observed_at ? new Date(insight.observed_at).toLocaleString() : 'No prediction recorded'}</time>
                  </div>
                  <ul className="mt-3 space-y-1">{insight.evidence.map((evidence) => <li key={evidence} className="text-sm text-ns-text-secondary">• {evidence}</li>)}</ul>
                  {insight.record_ids.length > 0 && <p className="mt-2 text-xs text-ns-text-muted">Prediction records: {insight.record_ids.join(', ')}</p>}
                </li>)}
              </ul>}
      </section>

      <section className="neo-card overflow-hidden" aria-labelledby="recovering-students-heading">
        <div className="border-b border-ns-divider px-5 py-4">
          <h2 id="recovering-students-heading" className="font-bold text-ink">Students Recovering</h2>
          <p className="mt-1 text-sm text-ink-soft">Students with three latest recorded predictions progressing High → Medium → Low.</p>
        </div>
        {recoveryLoading ? <p className="px-5 py-6 text-sm text-ink-soft">Loading recorded recovery history…</p>
          : recoveryError ? <p role="alert" className="px-5 py-6 text-sm text-ns-danger">Recovery history unavailable: {recoveryError}</p>
            : recovering.length === 0 ? <p className="px-5 py-6 text-sm text-ink-soft">No sustained recovery sequences are present in recorded predictions.</p>
              : <div className="overflow-x-auto"><table className="ns-table min-w-[760px]"><thead><tr><th>Student</th><th>Programme</th><th>Risk history</th><th>Model versions</th><th>Latest update</th></tr></thead><tbody>
                {recovering.map((student) => <tr key={student.student_id}>
                  <td><span className="font-semibold text-ns-text-primary">{student.student_name}</span><span className="block text-xs text-ns-text-muted">{student.student_id} · Year {student.year_level}</span></td>
                  <td>{student.programme}</td>
                  <td>{student.risk_history.map((entry) => `${entry.risk_level} ${entry.risk_score}%`).join(' → ')}</td>
                  <td>{student.risk_history.map((entry) => entry.model_version).join(' → ')}</td>
                  <td>{student.latest_updated_at ? new Date(student.latest_updated_at).toLocaleString() : 'Not recorded'}</td>
                </tr>)}
              </tbody></table></div>}
      </section>
    </div>
  );
}
