import { Building2 } from 'lucide-react';
import StatCard from '../../components/Cards/StatCard';
import DashboardHero from '../../components/DashboardHero';
import DataSourceNotice from '../../components/DataSourceNotice';
import AdminModelPerformanceCard from '../../components/AdminModelPerformanceCard';
import WeeklyBriefing from '../../components/WeeklyBriefing';
import BarChartCard from '../../components/Charts/BarChartCard';
import LineChartCard from '../../components/Charts/LineChartCard';
import PieChartCard from '../../components/Charts/PieChartCard';
import LoadingState from '../../components/LoadingState';
import { useDashboardData } from '../../hooks/useDashboardData';
import type { AdminAnalytics } from '../../types';

export default function AdminDashboard() {
  const { data, loading, error, source } = useDashboardData<AdminAnalytics>('admin');

  if (loading) return <LoadingState label="Loading university overview…" />;
  if (error) return <section className="neo-card p-6 text-sm text-ns-danger">{error}</section>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <DashboardHero
        icon={<Building2 size={42} strokeWidth={1.5} />}
      />

      {/* KPI stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-5">
        <StatCard title="Total Students" value={data.total_students.toLocaleString()} />
        <StatCard title="Active Students" value={data.active_students?.toLocaleString() ?? 'No data'} />
        <StatCard title="Avg Performance" value={data.average_performance == null ? 'No data' : `${data.average_performance}%`} />
        <StatCard title="Retention Rate" value={data.retention_rate == null ? 'No data' : `${data.retention_rate}%`} />
        <StatCard title="High Risk" value={data.high_risk_students.toLocaleString()} />
      </div>

      <WeeklyBriefing />
      <AdminModelPerformanceCard />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <PieChartCard
          title="Risk Distribution"
          subtitle="All students by risk level"
          data={data.risk_distribution}
          index={0}
        />
        <LineChartCard
          title="Attendance Trend"
          subtitle="Average attendance by month"
          data={data.attendance_trend.map((a) => ({ name: a.month, value: a.percentage }))}
          index={1}
        />
        <LineChartCard
          title="Performance Trend"
          subtitle="Average mark by month"
          data={data.performance_trend.map((p) => ({ name: p.month, value: p.average }))}
          index={2}
        />
      </div>

      {/* Programme comparison */}
      <BarChartCard
        title="Programme Comparison"
        subtitle="Average performance by programme"
        data={data.programme_comparison.map((p) => ({ name: p.programme, value: p.average }))}
        index={0}
      />
    </div>
  );
}
