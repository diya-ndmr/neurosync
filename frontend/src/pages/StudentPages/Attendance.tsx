import { motion } from 'framer-motion';
import LineChartCard from '../../components/Charts/LineChartCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useApiData } from '../../hooks/useApiData';
import { fetchStudentAttendanceSummary } from '../../services/liveData';
import { studentDemoAttendance } from '../../services/studentDemoData';

const attendanceFallback = {
  data: studentDemoAttendance,
  useWhenEmpty: (summary: typeof studentDemoAttendance) => summary.records.length === 0
};

export default function Attendance() {
  const { data, loading, error, source } = useApiData(fetchStudentAttendanceSummary, [], true, attendanceFallback);

  if (loading) return <LoadingState label="Loading your attendance record…" />;
  if (!data) return <div className="neo-card p-6 text-sm text-ns-danger" role="alert">{error || 'Attendance could not be loaded.'}</div>;

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-semibold text-ink">Attendance</h1>
        <p className="text-sm text-ink-soft">Recorded class attendance over the rolling three-month period ({data.period_start} – {data.period_end})</p>
      </motion.div>

      {error && <p className="text-sm text-ns-danger" role="alert">{error}</p>}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Metric label="Attendance rate" value={data.attendance_rate == null ? 'No recorded data' : `${data.attendance_rate}%`} />
        <Metric label="Classes attended" value={`${data.classes_attended}/${data.classes_counted}`} />
        <Metric label="Excused / approved leave" value={String(data.excused_absences)} />
      </div>
      <div className="grid grid-cols-1 gap-6">
        <LineChartCard
          title="Monthly breakdown"
          subtitle="Three consecutive 30-day periods. Only recorded class sessions are included; excused and approved-leave sessions are excluded from the rate."
          data={data.monthly_breakdown.filter((row) => row.percentage != null).map((row) => ({
            name: row.month,
            value: row.percentage!
          }))}
          index={0}
        />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {data.monthly_breakdown.map((period) => <section className="neo-card p-4" key={period.month}>
          <h2 className="font-semibold text-ink">{period.month}</h2>
          <p className="mt-1 text-xs text-ink-faint">{period.period_start} – {period.period_end}</p>
          <p className="mt-3 text-2xl font-bold text-ink">{period.percentage == null ? '—' : `${period.percentage}%`}</p>
          <p className="text-xs text-ink-soft">{period.attended}/{period.classes} counted classes attended</p>
        </section>)}
      </div>

      <section className="neo-card p-6" aria-labelledby="attendance-records-heading">
        <h2 id="attendance-records-heading" className="font-bold text-ink mb-4">Class attendance records</h2>
        {data.records.length === 0 ? <p className="text-sm text-ink-faint">No attendance records are available for this period.</p> : (
          <div className="overflow-x-auto"><table className="ns-table">
            <thead><tr><th scope="col">Date</th><th scope="col">Module</th><th scope="col">Class</th><th scope="col">Status</th></tr></thead>
            <tbody>{data.records.map((record) => <tr key={record.id}><td>{record.date}</td><td>{record.module}</td><td>{record.class_name}</td><td className="capitalize">{record.status.replace('_', ' ')}</td></tr>)}</tbody>
          </table></div>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="neo-card p-5"><p className="text-sm text-ink-soft">{label}</p><p className="mt-2 text-2xl font-bold text-ink">{value}</p></div>;
}
