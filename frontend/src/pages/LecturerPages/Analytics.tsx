import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import BarChartCard from '../../components/Charts/BarChartCard';
import LineChartCard from '../../components/Charts/LineChartCard';
import PieChartCard from '../../components/Charts/PieChartCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { useDashboardData } from '../../hooks/useDashboardData';
import type { LecturerDashboardData } from '../../types';

interface LecturerModule {
  module_id: string;
  module_code: string;
  module_name: string;
}

interface AssessmentIntelligence {
  status: 'ANOMALY_DETECTED' | 'NO_ANOMALY_DETECTED' | 'INSUFFICIENT_DATA' | 'INSUFFICIENT_COHORT';
  message: string;
  interpretation?: string;
  comparison: {
    current_assessment: string;
    current_average: number;
    current_student_count: number;
    previous_assessment: string;
    previous_average: number;
    previous_student_count: number;
    change_percentage_points: number;
  } | null;
}

export default function Analytics() {
  const { token } = useAuth();
  const { data, loading, error, source } = useDashboardData<LecturerDashboardData>('lecturer');
  const [modules, setModules] = useState<LecturerModule[]>([]);
  const [selectedModule, setSelectedModule] = useState('');
  const [assessmentIntelligence, setAssessmentIntelligence] = useState<AssessmentIntelligence | null>(null);
  const [assessmentLoading, setAssessmentLoading] = useState(false);
  const [assessmentError, setAssessmentError] = useState('');

  useEffect(() => {
    if (!token) return;
    let active = true;
    api.get<LecturerModule[]>('/workflow/lecturer/modules', token)
      .then((items) => {
        if (!active) return;
        setModules(items);
        setSelectedModule((current) => current || items[0]?.module_id || '');
      })
      .catch((requestError: Error) => {
        if (active) setAssessmentError(requestError.message);
      });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!token || !selectedModule) return;
    let active = true;
    setAssessmentLoading(true);
    setAssessmentError('');
    api.get<AssessmentIntelligence>(`/workflow/lecturer/modules/${selectedModule}/assessment-intelligence`, token)
      .then((result) => { if (active) setAssessmentIntelligence(result); })
      .catch((requestError: Error) => { if (active) setAssessmentError(requestError.message); })
      .finally(() => { if (active) setAssessmentLoading(false); });
    return () => { active = false; };
  }, [selectedModule, token]);

  if (loading) return <LoadingState label="Loading class analytics…" />;
  if (error || !data) {
    return <section className="neo-card p-6 text-sm text-ns-danger">{error ?? 'Analytics unavailable.'}</section>;
  }

  const strongest = [...data.module_performance].sort((a, b) => b.mark - a.mark)[0];
  const weakest = [...data.module_performance].sort((a, b) => a.mark - b.mark)[0];

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-extrabold text-ink">Performance Analytics</h1>
        <p className="text-sm text-ink-soft mt-1">
          Cohort trends and assessment comparisons from recorded module data
        </p>
      </motion.div>

      <section className="neo-card p-5" aria-labelledby="assessment-intelligence-title">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 id="assessment-intelligence-title" className="font-bold text-ink">Assessment review</h2>
            <p className="mt-1 text-sm text-ink-soft">Compare completed assessment averages within an authorized module.</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-soft">
            Module
            <select
              aria-label="Select module for assessment intelligence"
              className="neo-input min-w-52 py-2"
              value={selectedModule}
              onChange={(event) => setSelectedModule(event.target.value)}
            >
              {modules.map((module) => <option key={module.module_id} value={module.module_id}>{module.module_code} · {module.module_name}</option>)}
            </select>
          </label>
        </div>
        <div className="mt-4 border-t border-ns-divider pt-4" aria-live="polite">
          {assessmentLoading ? <p className="text-sm text-ink-soft">Loading assessment comparison…</p>
            : assessmentError ? <p role="alert" className="text-sm text-ns-danger">Assessment comparison is unavailable: {assessmentError}</p>
              : assessmentIntelligence?.comparison ? <>
                <p className={`text-sm font-semibold ${assessmentIntelligence.status === 'ANOMALY_DETECTED' ? 'text-ns-warning' : 'text-ink'}`}>{assessmentIntelligence.message}</p>
                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {[
                    { title: assessmentIntelligence.comparison.previous_assessment, average: assessmentIntelligence.comparison.previous_average, count: assessmentIntelligence.comparison.previous_student_count },
                    { title: assessmentIntelligence.comparison.current_assessment, average: assessmentIntelligence.comparison.current_average, count: assessmentIntelligence.comparison.current_student_count }
                  ].map((assessment) => <div key={assessment.title} className="rounded-md border border-ns-border bg-white p-3">
                    <p className="text-xs text-ns-text-muted">{assessment.title}</p>
                    <p className="mt-1 text-lg font-semibold text-ns-text-primary">{assessment.average}% <span className="text-xs font-normal text-ns-text-muted">average · {assessment.count} submissions</span></p>
                  </div>)}
                </div>
                <p className="mt-3 text-xs text-ns-text-muted">{assessmentIntelligence.interpretation}</p>
              </> : <p className="text-sm text-ink-soft">{assessmentIntelligence?.message ?? 'Select a module to inspect completed assessment results.'}</p>}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <LineChartCard
          title="Class Performance Trend"
          subtitle="Cohort attendance by period"
          data={data.class_performance.map((p) => ({
            name: p.month,
            value: p.average
          }))}
          index={0}
        />
        <BarChartCard
          title="Module Performance"
          subtitle="Average mark by module"
          data={data.module_performance.slice(0, 8).map((m) => ({
            name: m.module,
            value: m.mark
          }))}
          index={1}
        />
        <PieChartCard
          title="Risk Distribution"
          subtitle="Students by risk level"
          data={data.risk_distribution}
          index={2}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="neo-card p-6"
      >
        <h3 className="font-bold text-ink mb-3">Analytics Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              title: 'Strongest module',
              color: 'text-emerald-600',
              desc: strongest
                ? `${strongest.module} leads the cohort with an average of ${strongest.mark}% across the students you teach.`
                : 'No module performance recorded yet.'
            },
            {
              title: 'Area of concern',
              color: 'text-red-500',
              desc: weakest
                ? `${weakest.module} has the lowest cohort average (${weakest.mark}%) — worth investigating support needs.`
                : 'No module performance recorded yet.'
            },
            {
              title: 'Follow-up needed',
              color: 'text-brand-600',
              desc: `${data.students_at_risk} of ${data.total_students} students currently show an academic indicator that warrants follow-up (average attendance ${data.average_attendance}%).`
            }
          ].map((insight, i) => (
            <motion.div
              key={insight.title}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.1 }}
              className="rounded-2xl bg-white/60 border border-brand-100/60 p-5"
            >
              <h4 className={`font-bold ${insight.color}`}>{insight.title}</h4>
              <p className="text-sm text-ink-soft mt-1 leading-relaxed">{insight.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
