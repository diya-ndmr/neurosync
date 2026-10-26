import { motion } from 'framer-motion';
import { useId } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { PerformancePoint } from '../../types';
import { cn } from '../../utils/helpers';

interface Props {
  average: number | null;
  trend: 'improving' | 'declining' | 'stable';
  history: PerformancePoint[];
}

const trendMeta = {
  improving: { label: 'Improving', color: 'text-emerald-600' },
  declining: { label: 'Declining', color: 'text-red-500' },
  stable: { label: 'Stable', color: 'text-ink-faint' }
};

export default function AcademicPerformanceCard({ average, trend, history }: Props) {
  const meta = trendMeta[trend];
  const gradientId = `performance-gradient-${useId().replace(/:/g, '')}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-6"
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-ink">Academic performance overview</h3>
          <p className="text-xs text-ink-faint">Assessment trend</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-ns-surface-secondary px-3 py-2">
            <p className="text-[10px] font-medium text-ns-text-muted">Current average</p>
            <p className="text-sm font-bold text-ns-text-primary">{average === null ? 'Not recorded' : `${average}%`}</p>
          </div>
          <span className={cn('rounded-lg border px-3 py-2 text-xs font-semibold', meta.color, trend === 'improving' ? 'border-emerald-200 bg-emerald-50' : trend === 'declining' ? 'border-red-200 bg-red-50' : 'border-ns-border bg-ns-surface-secondary')}>
            {meta.label}
          </span>
        </div>
      </div>

      {history.length === 0 ? (
        <p className="chart-empty mt-4 flex h-64 items-center justify-center rounded-xl border border-dashed border-ns-border text-sm text-ink-faint">No graded assessments are available yet.</p>
      ) : <div className="chart-frame h-64 mt-3 rounded-xl p-2" role="img" aria-label={`Academic performance history; current average ${average === null ? 'not available' : `${average} percent`}`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--ns-dashboard-accent)" stopOpacity={0.3} />
                <stop offset="100%" stopColor="var(--ns-dashboard-accent)" stopOpacity={0.015} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="4 6" stroke="var(--ns-divider)" vertical={false} />
            <XAxis dataKey="month" tick={{ fill: 'var(--ns-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis domain={[40, 100]} tick={{ fill: 'var(--ns-text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: '1px solid var(--ns-border)',
                background: 'var(--ns-surface)',
                boxShadow: 'var(--ns-shadow-popover)',
                fontSize: 13
              }}
              formatter={(v) => [`${v}%`, 'Average']}
            />
            <Area type="monotone" dataKey="average" stroke="var(--ns-dashboard-accent)" strokeWidth={3} fill={`url(#${gradientId})`} activeDot={{ r: 5, strokeWidth: 2, stroke: 'var(--ns-surface)' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>}
      {history.length > 0 && <details className="mt-2 text-sm">
        <summary className="min-h-11 cursor-pointer py-3 font-semibold text-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2">View chart data as a table</summary>
        <div className="overflow-x-auto"><table className="ns-table"><caption className="sr-only">Academic performance history</caption><thead><tr><th scope="col">Period</th><th scope="col">Average</th></tr></thead><tbody>{history.map((point) => <tr key={point.month}><th scope="row" className="text-left">{point.month}</th><td>{point.average}%</td></tr>)}</tbody></table></div>
      </details>}
    </motion.div>
  );
}
