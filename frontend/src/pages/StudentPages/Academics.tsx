import { motion } from 'framer-motion';
import AdditionalLearningDataPanel from '../../components/AdditionalLearningDataPanel';
import BarChartCard from '../../components/Charts/BarChartCard';
import ModuleAssessmentsPanel from '../../components/ModuleAssessmentsPanel';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useApiData } from '../../hooks/useApiData';
import {
  fetchStudentAssessments,
  fetchStudentDashboard,
  fetchStudentStudySessions,
  fetchSupplementaryAssessmentFeedback,
} from '../../services/liveData';
import {
  studentDemoAssessments,
  studentDemoFeedback,
  studentDemoStudySessions
} from '../../services/studentDemoData';
import { studentDashboard } from '../../services/mockData';

const assessmentFallback = { data: studentDemoAssessments, useWhenEmpty: (rows: typeof studentDemoAssessments) => rows.length === 0 };
const dashboardFallback = {
  data: studentDashboard,
  useWhenEmpty: (dashboard: typeof studentDashboard) => dashboard.performance.module_breakdown.length === 0
};
const feedbackFallback = { data: studentDemoFeedback, useWhenEmpty: (rows: typeof studentDemoFeedback) => rows.length === 0 };
const studyFallback = { data: studentDemoStudySessions, useWhenEmpty: (rows: typeof studentDemoStudySessions) => rows.length === 0 };

export default function Academics() {
  const { data: assessments, loading, error, source: assessmentSource } = useApiData(fetchStudentAssessments, [], true, assessmentFallback);
  const { data: dashboard, source: dashboardSource } = useApiData(fetchStudentDashboard, [], true, dashboardFallback);
  const { data: supplementaryFeedback, loading: feedbackLoading, error: feedbackError, source: feedbackSource } =
    useApiData(fetchSupplementaryAssessmentFeedback, [], true, feedbackFallback);
  const { data: studySessions, loading: studyLoading, error: studyError, source: studySource } =
    useApiData(fetchStudentStudySessions, [], true, studyFallback);

  if (loading) return <LoadingState label="Loading your assessment record..." />;

  const rows = assessments ?? [];
  const moduleBreakdown = dashboard?.performance.module_breakdown ?? [];
  const sources = [assessmentSource, dashboardSource, feedbackSource, studySource].filter((source) => source && source !== 'live');
  const source = sources.includes('offline-demo') ? 'offline-demo' : sources.length ? 'demo-sample' : 'live';

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-semibold text-ink">Academics</h1>
        <p className="text-sm text-ink-soft">Your detailed assessment history</p>
      </motion.div>

      {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-ns-danger">Your assessment record could not be loaded: {error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BarChartCard
          title="Module Performance"
          subtitle="Latest average by module"
          data={moduleBreakdown.map((m) => ({
            name: m.module,
            value: m.mark
          }))}
          index={0}
        />
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="neo-card p-6"
        >
          <h3 className="font-bold text-ink mb-4">My modules - select one for quizzes, exams and feedback</h3>
          <ModuleAssessmentsPanel assessments={rows} />
        </motion.div>
      </div>
      <AdditionalLearningDataPanel
        feedback={supplementaryFeedback}
        feedbackLoading={feedbackLoading}
        feedbackError={feedbackError}
        studySessions={studySessions}
        studyLoading={studyLoading}
        studyError={studyError}
      />
    </div>
  );
}
