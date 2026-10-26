import { motion } from 'framer-motion';
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

interface Props {
  title: string;
  subtitle?: string;
  data: { name: string; value: number }[];
  index?: number;
}

const riskColorFor = (name: string, index: number) => {
  switch (name.toUpperCase()) {
    case 'LOW': return 'var(--ns-success)';
    case 'MEDIUM': return 'var(--ns-warning)';
    case 'HIGH': return 'var(--ns-danger)';
    default: return ['var(--ns-chart-blue)', 'var(--ns-aqua)', 'var(--ns-chart-neutral)'][index % 3];
  }
};

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
        <div>
          <h3 className="font-semibold text-ns-text-primary">{title}</h3>
          {subtitle && <p className="text-xs text-ns-text-muted mt-0.5">{subtitle}</p>}
        </div>
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
              innerRadius={62}
              outerRadius={88}
              paddingAngle={3}
              stroke="var(--ns-surface)"
              strokeWidth={3}
            >
              {data.map((entry, i) => (
                <Cell key={entry.name} fill={riskColorFor(entry.name, i)} />
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
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-3xl font-bold tracking-tight text-ns-text-primary">{total}</span>
        </div>
      </div>}

      {data.length > 0 && total > 0 && <div className="mt-5 grid grid-cols-1 gap-2">
        {data.map((d, i) => (
          <div key={d.name} className="flex items-center gap-3 rounded-lg border border-ns-border bg-ns-surface-secondary/70 px-3 py-2">
            <span
              aria-hidden="true"
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: riskColorFor(d.name, i) }}
            />
            <p className="min-w-0 flex-1 truncate text-xs font-semibold uppercase tracking-wide text-ns-text-secondary">{d.name}</p>
            <p className="text-xs font-bold text-ns-text-primary">{d.value}</p>
            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-ns-border" aria-hidden="true">
              <div className="h-full rounded-full" style={{ width: `${Math.round((d.value / total) * 100)}%`, background: riskColorFor(d.name, i) }} />
            </div>
            <p className="w-9 text-right text-xs font-semibold text-ns-text-muted">{Math.round((d.value / total) * 100)}%</p>
          </div>
        ))}
      </div>}
    </motion.div>
  );
}
