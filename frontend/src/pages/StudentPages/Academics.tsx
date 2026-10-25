import { motion } from 'framer-motion';
import AdditionalLearningDataPanel from '../../components/AdditionalLearningDataPanel';
import BarChartCard from '../../components/Charts/BarChartCard';
import ModuleAssessmentsPanel from '../../components/ModuleAssessmentsPanel';
import LoadingState from '../../components/LoadingState';
import { useApiData } from '../../hooks/useApiData';
import {
  fetchStudentAssessments,
  fetchStudentDashboard,
  fetchStudentStudySessions,
  fetchSupplementaryAssessmentFeedback,
} from '../../services/liveData';

export default function Academics() {
  const { data: assessments, loading } = useApiData(fetchStudentAssessments);
  const { data: dashboard } = useApiData(fetchStudentDashboard);
  const { data: supplementaryFeedback, loading: feedbackLoading, error: feedbackError } =
    useApiData(fetchSupplementaryAssessmentFeedback);
  const { data: studySessions, loading: studyLoading, error: studyError } =
    useApiData(fetchStudentStudySessions);

  if (loading) return <LoadingState label="Loading your assessment record..." />;

  const rows = assessments ?? [];
  const moduleBreakdown = dashboard?.performance.module_breakdown ?? [];

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-semibold text-ink">Academics</h1>
        <p className="text-sm text-ink-soft">Your detailed assessment history</p>
      </motion.div>

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
