import { motion } from 'framer-motion';
import BarChartCard from '../../components/Charts/BarChartCard';
import LoadingState from '../../components/LoadingState';
import { useApiData } from '../../hooks/useApiData';
import { fetchStudentAssessments, fetchStudentDashboard } from '../../services/liveData';

export default function Academics() {
  const { data: assessments, loading } = useApiData(fetchStudentAssessments);
  const { data: dashboard } = useApiData(fetchStudentDashboard);

  if (loading) return <LoadingState label="Loading your assessment record…" />;

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
          <h3 className="font-bold text-ink mb-4">Recent Assessments</h3>
          <div className="space-y-3">
            {rows.length === 0 && <p className="text-sm text-ink-faint">No assessments recorded yet.</p>}
            {rows.map((a, i) => (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 * i }}
                className="flex items-center justify-between rounded-2xl bg-white/60 border border-brand-100/60 p-3.5"
              >
                <div>
                  <p className="text-sm font-bold text-ink">{a.module}</p>
                  <p className="text-xs text-ink-faint">
                    {a.module_code} · {a.assessment_type}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={`text-lg font-extrabold ${
                      a.mark >= 75 ? 'text-emerald-600' : a.mark >= 60 ? 'text-amber-600' : 'text-red-500'
                    }`}
                  >
                    {a.mark}%
                  </p>
                  <p className="text-[10px] text-ink-faint">{new Date(a.assessment_date).toLocaleDateString()}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
