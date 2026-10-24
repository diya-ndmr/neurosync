import { motion } from 'framer-motion';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { riskColor } from '../../utils/helpers';

interface Props {
  title: string;
  subtitle?: string;
  data: { name: string; value: number }[];
  index?: number;
}

const RISK_COLORS = ['var(--ns-success)', 'var(--ns-warning)', 'var(--ns-danger)'];

export default function PieChartCard({ title, subtitle, data, index = 0 }: Props) {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.1 }}
      className="neo-card p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-ns-text-primary">{title}</h3>
        {subtitle && <p className="text-xs text-ns-text-muted mt-0.5">{subtitle}</p>}
      </div>

      {data.length === 0 || total === 0 ? <div className="mt-4 flex h-56 items-center justify-center rounded-md border border-dashed border-ns-border text-sm text-ns-text-muted">No recorded data</div> : <div className="relative h-56 mt-4" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={85}
              paddingAngle={4}
              stroke="none"
            >
              {data.map((entry, i) => (
                <Cell key={entry.name} fill={RISK_COLORS[i % RISK_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                borderRadius: 12,
                border: '1px solid var(--ns-border)',
                background: 'var(--ns-surface)',
                boxShadow: 'var(--ns-shadow-popover)',
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--ns-text-primary)'
              }}
              formatter={(v, name) => [`${v} STUDENTS`, name.toString().toUpperCase()]}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-3xl font-bold text-ns-text-primary">{total}</span>
          <span className="text-[9px] font-semibold uppercase tracking-widest text-ns-text-muted">Total</span>
        </div>
      </div>}

      {data.length > 0 && total > 0 && <div className="mt-6 grid grid-cols-3 gap-2">
        {data.map((d, i) => (
          <div key={d.name} className="rounded-lg bg-ns-surface-secondary px-2 py-2 border border-ns-border text-center">
            <div
              aria-hidden="true"
              className="w-2.5 h-2.5 rounded-full mx-auto mb-1.5"
              style={{ background: RISK_COLORS[i % RISK_COLORS.length] }}
            />
            <p className="text-sm font-semibold text-ns-text-primary">{d.value} <span className="font-normal">({Math.round((d.value / total) * 100)}%)</span></p>
            <p className="mt-1 break-words text-xs font-semibold uppercase text-ns-text-muted">{d.name}</p>
          </div>
        ))}
      </div>}
    </motion.div>
  );
}
