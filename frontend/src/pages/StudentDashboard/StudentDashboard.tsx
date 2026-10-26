import WelcomeCard from '../../components/Cards/WelcomeCard';
import AcademicPerformanceCard from '../../components/Cards/AcademicPerformanceCard';
import RiskPredictionCard from '../../components/Cards/RiskPredictionCard';
import WellbeingCard from '../../components/Cards/WellbeingCard';
import RecommendationCard from '../../components/Cards/RecommendationCard';
import ModulePerformanceCard from '../../components/Cards/ModulePerformanceCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useDashboardData } from '../../hooks/useDashboardData';
import type { StudentDashboardData } from '../../types';
import { api } from '../../services/api';
import { studentDashboard } from '../../services/mockData';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApiData } from '../../hooks/useApiData';
import { fetchStudentAttendanceSummary } from '../../services/liveData';
import { studentDemoAttendance } from '../../services/studentDemoData';

const attendanceFallback = {
  data: studentDemoAttendance,
  useWhenEmpty: (summary: typeof studentDemoAttendance) => summary.records.length === 0
};

export default function StudentDashboard() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const { showToast } = useToast();
  const [supportOpen, setSupportOpen] = useState(false);
  const [requestType, setRequestType] = useState('Academic support');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const { data, loading, error, source, refresh } = useDashboardData<StudentDashboardData>('student');
  const { data: attendanceSummary, loading: attendanceLoading, error: attendanceError, source: attendanceSource } =
    useApiData(fetchStudentAttendanceSummary, [], true, attendanceFallback);
  const [completingRecommendation, setCompletingRecommendation] = useState<string | null>(null);

  const completeRecommendation = async (recommendationId: string) => {
    if (!token || source !== 'live') return;
    setCompletingRecommendation(recommendationId);
    try {
      await api.patch(`/predictions/recommendations/${recommendationId}/complete`, {}, token);
      showToast('Suggestion marked complete.');
      refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not update suggestion.', 'error');
    } finally {
      setCompletingRecommendation(null);
    }
  };

  if (loading) return <LoadingState label="Analysing your academic profile…" />;
  if (error) return <section className="neo-card p-6 text-sm text-ns-danger">{error}</section>;
  if (!data) return null;

  const { student, performance, risk, recommendations, wellbeing } = data;
  const monthlyAttendance = attendanceSummary?.monthly_breakdown ?? [];
  const latestAttendanceMonth = monthlyAttendance[monthlyAttendance.length - 1];
  const firstAttendanceMonth = monthlyAttendance[0];
  const displayRecommendations = recommendations.length ? recommendations : studentDashboard.recommendations;
  const dataSource = source === 'offline-demo' || attendanceSource === 'offline-demo'
    ? 'offline-demo'
    : source === 'demo-sample' || attendanceSource === 'demo-sample' || recommendations.length === 0
      ? 'demo-sample'
      : source;

  return (
    <div className="student-dashboard space-y-6">
      <DataSourceNotice source={dataSource} />
      {supportOpen && <div className="fixed inset-0 z-50 flex items-center justify-center p-4"><button aria-label="Close support request" className="absolute inset-0 bg-ns-black/40" onClick={() => setSupportOpen(false)} /><form className="relative w-full max-w-lg rounded-lg border border-ns-border bg-white p-5 shadow-xl" onSubmit={async (event) => { event.preventDefault(); if (!token || !message.trim()) return; setSending(true); try { await api.post('/support-requests', { request_type: requestType, message }, token); setMessage(''); setSupportOpen(false); showToast('Your support request was sent.'); } catch (error) { showToast(error instanceof Error ? error.message : 'Could not send support request.', 'error'); } finally { setSending(false); } }}><h2 className="text-lg font-semibold">Request support</h2><p className="mt-1 text-sm text-ns-text-secondary">Tell the support team what would help.</p><label className="mt-4 block text-sm font-medium">Area<select className="neo-input mt-1" value={requestType} onChange={(event) => setRequestType(event.target.value)}><option>Academic support</option><option>Attendance support</option><option>Wellbeing support</option><option>Financial or personal support</option><option>Other</option></select></label><label className="mt-4 block text-sm font-medium">Message<textarea className="neo-input mt-1" rows={5} minLength={5} maxLength={2000} required value={message} onChange={(event) => setMessage(event.target.value)} placeholder="What would you like help with?" /></label><div className="mt-4 flex justify-end gap-2"><button type="button" className="neo-btn px-4 py-2 text-sm" onClick={() => setSupportOpen(false)}>Cancel</button><button type="submit" disabled={sending || !message.trim()} className="neo-btn inline-flex items-center gap-2 px-4 py-2 text-sm">{sending ? 'Sending…' : 'Send request'}</button></div></form></div>}
      <WelcomeCard
        student={student}
        academicAverage={performance.current_average}
        academicTrend={performance.trend}
        onRequestSupport={() => setSupportOpen(true)}
      />

      <div className="grid grid-cols-1 gap-6 min-[900px]:grid-cols-[minmax(0,1.8fr)_minmax(250px,1fr)]">
        <AcademicPerformanceCard
          average={performance.current_average}
          trend={performance.trend}
          history={performance.history}
        />
        <ModulePerformanceCard modules={performance.module_breakdown} />
      </div>

      <section aria-label="Student support" className="space-y-4">
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
          <section className="neo-card p-5" aria-labelledby="dashboard-attendance-heading">
            <div className="flex items-start justify-between gap-2"><div><h3 id="dashboard-attendance-heading" className="font-semibold text-ink">Attendance</h3><p className="text-xs text-ink-faint">Rolling last 3 months</p></div><button type="button" onClick={() => navigate('/student/attendance')} className="text-xs font-semibold text-brand-800">View details</button></div>
            {attendanceLoading ? <p className="mt-5 text-sm text-ink-faint">Loading recorded attendance…</p> : attendanceError ? <p role="alert" className="mt-5 text-sm text-ns-danger">{attendanceError}</p> : attendanceSummary && attendanceSummary.classes_counted > 0 ? <>
              <p className="mt-4 text-3xl font-bold text-ink">{attendanceSummary.attendance_rate == null ? '—' : `${attendanceSummary.attendance_rate}%`}</p>
              <p className="text-xs text-ink-soft">Attendance rate · {attendanceSummary.classes_attended}/{attendanceSummary.classes_counted} classes attended</p>
              <div className="mt-4 space-y-3">{monthlyAttendance.map((month) => <div key={month.month} className="text-xs"><div className="mb-1 flex items-center justify-between gap-2"><span className="truncate text-ink-soft">{month.month}</span><span className="font-semibold text-ink">{month.percentage == null ? '—' : `${month.percentage}%`}</span></div><div className="module-progress-track"><div className="module-progress-fill" style={{ width: `${Math.min(100, Math.max(0, month.percentage ?? 0))}%` }} /></div></div>)}</div>
              {monthlyAttendance.length > 1 && firstAttendanceMonth?.percentage != null && latestAttendanceMonth?.percentage != null && firstAttendanceMonth.percentage > latestAttendanceMonth.percentage && <p className="mt-3 text-xs text-ns-warning">Recorded attendance has decreased over the displayed months. Excused absences are excluded from the rate.</p>}
            </> : <p className="mt-5 text-sm text-ink-faint">No class attendance has been recorded.</p>}
          </section>
          <WellbeingCard
            moodScore={wellbeing.mood_score}
            stressLevel={wellbeing.stress_level}
            lastCheckin={wellbeing.last_checkin}
            onCheckin={() => navigate('/student/wellbeing')}
          />
          <RecommendationCard recommendations={displayRecommendations} onComplete={completeRecommendation} completingId={completingRecommendation} readOnly={source !== 'live' || recommendations.length === 0} />
        </div>
      </section>

      <RiskPredictionCard risk={risk} />
    </div>
  );
}
