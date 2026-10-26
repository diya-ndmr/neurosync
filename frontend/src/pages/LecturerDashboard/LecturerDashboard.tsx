import { motion } from 'framer-motion';
import { GraduationCap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StatCard from '../../components/Cards/StatCard';
import DashboardHero from '../../components/DashboardHero';
import BarChartCard from '../../components/Charts/BarChartCard';
import LineChartCard from '../../components/Charts/LineChartCard';
import PieChartCard from '../../components/Charts/PieChartCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import WeeklyBriefing from '../../components/WeeklyBriefing';
import ActionQueue from '../../components/ActionQueue';
import { useDashboardData } from '../../hooks/useDashboardData';
import { riskBg, cn } from '../../utils/helpers';
import type { LecturerDashboardData } from '../../types';

export default function LecturerDashboard() {
  const navigate = useNavigate();
  const { data, loading, error, source } = useDashboardData<LecturerDashboardData>('lecturer');

  if (loading) return <LoadingState label="Loading class overview…" />;
  if (error) return <section className="neo-card p-6 text-sm text-ns-danger">{error}</section>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <DashboardHero
        icon={<GraduationCap size={42} strokeWidth={1.5} />}
      />

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard title="Students" value={data.total_students} />
        <StatCard title="Average mark" value={`${data.average_mark}%`} />
        <StatCard title="Average attendance" value={`${data.average_attendance}%`} />
        <StatCard title="Students needing support" value={data.students_at_risk} subtitle="Flagged for follow-up" />
      </div>

      <WeeklyBriefing />
      <ActionQueue />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <PieChartCard
            title="Risk distribution"
            subtitle="Students by risk level"
            data={data.risk_distribution}
            index={0}
          />
        </div>
        <div className="lg:col-span-2">
          <LineChartCard
            title="Class performance"
            subtitle="Average marks over time"
            data={data.class_performance.map((p) => ({ name: p.month, value: p.average }))}
            index={1}
          />
        </div>
      </div>

      {/* Risk monitor table */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2 }}
        className="neo-card p-5 md:p-6"
      >
        <div className="flex items-center justify-between mb-8">
          <div>
            <h3 className="font-semibold text-ns-text-primary text-lg">Risk monitor</h3>
            <p className="text-xs text-ns-text-muted mt-0.5">Students requiring follow-up</p>
          </div>
          <span className="px-3 py-1 rounded-full bg-red-50 border border-red-200 text-ns-danger text-xs font-semibold">
            {data.students_at_risk} students flagged for follow-up
          </span>
        </div>

        <div className="overflow-x-auto -mx-2 px-2">
          <table className="ns-table min-w-[760px]">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ns-text-secondary border-b border-ns-border">
                <th className="pb-4 px-4">Student</th>
                <th className="pb-4 px-4">Identifier</th>
                <th className="pb-4 px-4">Module</th>
                <th className="pb-4 px-4">Performance</th>
                <th className="pb-4 px-4">Presence</th>
                <th className="pb-4 px-4">Risk level</th>
                <th className="pb-4 px-4">Reason</th>
                <th className="pb-4 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.students.map((s, i) => (
                <motion.tr
                  key={s.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-ns-divider hover:bg-brand-50/60 transition-colors"
                >
                  <td className="py-3 px-4 font-semibold text-ns-text-primary">{s.name}</td>
                  <td className="py-3 px-4 text-ns-text-muted font-mono text-xs">{s.student_number}</td>
                  <td className="py-3 px-4 text-ns-text-secondary text-xs">{s.module}</td>
                  <td className="py-3 px-4 font-semibold text-brand-800">{s.average_mark}%</td>
                  <td className="py-3 px-4">
                    <span className={s.attendance < 70 ? 'text-ns-danger font-semibold' : 'text-ns-text-secondary'}>
                      {s.attendance}%
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={cn('px-2 py-1 rounded-full text-[10px] font-semibold uppercase border',
                      s.risk_level === 'HIGH' ? 'bg-red-50 text-ns-danger border-red-200' :
                      s.risk_level === 'MEDIUM' ? 'bg-amber-50 text-ns-warning border-amber-200' :
                      'bg-emerald-50 text-ns-success border-emerald-200'
                    )}>
                      {s.risk_level}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-xs text-ns-text-secondary max-w-[220px] leading-snug">"{s.ai_explanation}"</td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button aria-label={`View ${s.name}`} onClick={() => navigate(`/lecturer/students/${s.id}`)} className="min-h-10 rounded border border-ns-border bg-white px-3 text-xs font-medium text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors">
                        View
                      </button>
                      <button aria-label={`Contact ${s.name}`} onClick={() => navigate(`/lecturer/students/${s.id}`)} className="min-h-10 rounded border border-ns-border bg-white px-3 text-xs font-medium text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors">
                        Contact
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
