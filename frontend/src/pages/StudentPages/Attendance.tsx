import { motion } from 'framer-motion';
import AttendanceCard from '../../components/Cards/AttendanceCard';
import LineChartCard from '../../components/Charts/LineChartCard';
import LoadingState from '../../components/LoadingState';
import { useApiData } from '../../hooks/useApiData';
import { fetchStudentAttendance, fetchStudentDashboard } from '../../services/liveData';

export default function Attendance() {
  const { data: dashboard, loading } = useApiData(fetchStudentDashboard);
  const { data: records } = useApiData(fetchStudentAttendance);

  if (loading || !dashboard) return <LoadingState label="Loading your attendance record…" />;

  // Attendance is stored per module, so the page groups the enrolled modules and
  // averages the recorded percentages instead of showing placeholder figures.
  const byModule = new Map<string, { module: string; total: number; count: number }>();
  for (const record of records ?? []) {
    const current = byModule.get(record.module_code) ?? { module: record.module, total: 0, count: 0 };
    current.total += record.attendance_percentage;
    current.count += 1;
    byModule.set(record.module_code, current);
  }
  const moduleAttendance = [...byModule.values()].map((entry) => ({
    module: entry.module,
    percentage: Math.round((entry.total / entry.count) * 10) / 10
  }));

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-semibold text-ink">Attendance</h1>
        <p className="text-sm text-ink-soft">Your attendance history and trends</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AttendanceCard
          current={dashboard.attendance.current}
          previous={dashboard.attendance.previous}
          change={dashboard.attendance.change}
          status={dashboard.attendance.status}
        />
        <LineChartCard
          title="Attendance Trend"
          subtitle="Monthly attendance percentage"
          data={dashboard.attendance.history.map((h) => ({
            name: h.month,
            value: h.percentage
          }))}
          index={0}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="neo-card p-6"
      >
        <h3 className="font-bold text-ink mb-4">Attendance by Module</h3>
        {moduleAttendance.length === 0 && (
          <p className="text-sm text-ink-faint">No module attendance recorded yet.</p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {moduleAttendance.map((m, i) => (
            <motion.div
              key={m.module}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.05 * i }}
              className="rounded-2xl bg-white/60 border border-brand-100/60 p-4 text-center"
            >
              <p
                className={`text-2xl font-extrabold ${
                  m.percentage >= 85
                    ? 'text-emerald-600'
                    : m.percentage >= 75
                      ? 'text-amber-600'
                      : 'text-red-500'
                }`}
              >
                {m.percentage}%
              </p>
              <p className="text-xs font-semibold text-ink-soft mt-1">{m.module}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
