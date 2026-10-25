import { motion } from 'framer-motion';
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-ink">Academic performance</h3>
          <p className="text-xs text-ink-faint">Current average across modules</p>
        </div>
        {average !== null && <span className={cn('flex items-center gap-1 text-sm font-bold', meta.color)}>{meta.label}</span>}
      </div>

      <div className="flex items-end gap-3 mb-2">
        <span className="text-4xl font-extrabold text-ink">{average === null ? '—' : `${average}%`}</span>
      </div>

      {history.length === 0 ? (
        <p className="mt-4 text-sm text-ink-faint">No graded assessments are available yet.</p>
      ) : <div className="h-48 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--ns-primary)" stopOpacity={0.24} />
                <stop offset="100%" stopColor="var(--ns-primary)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ns-divider)" vertical={false} />
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
            <Area type="monotone" dataKey="average" stroke="var(--ns-primary-dark)" strokeWidth={2.5} fill="url(#perfGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>}
    </motion.div>
  );
}
