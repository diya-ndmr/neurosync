import { motion } from 'framer-motion';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts';

interface Props {
  title: string;
  subtitle?: string;
  data: { name: string; value: number }[];
  dataKey?: string;
  color?: string;
  index?: number;
}

export default function LineChartCard({
  title,
  subtitle,
  data,
  dataKey = 'value',
  color = 'var(--ns-primary)',
  index = 0
}: Props) {
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

      {data.length === 0 ? <div className="mt-4 flex h-64 items-center justify-center rounded-md border border-dashed border-ns-border text-sm text-ns-text-muted">No recorded data</div> : <div className="h-64 mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--ns-divider)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: 'var(--ns-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--ns-text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
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
            />
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={3}
              dot={{ r: 3, fill: color, strokeWidth: 2, stroke: 'var(--ns-surface)' }}
              activeDot={{ r: 5, stroke: 'var(--ns-primary-dark)', strokeWidth: 2, fill: 'var(--ns-surface)' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>}
      {data.length > 0 && <details className="mt-3 text-sm">
        <summary className="min-h-11 cursor-pointer py-3 font-semibold text-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2">View chart data as a table</summary>
        <div className="overflow-x-auto"><table className="ns-table"><caption className="sr-only">{title} chart values</caption><thead><tr><th scope="col">Category</th><th scope="col">{dataKey}</th></tr></thead><tbody>{data.map((item) => <tr key={item.name}><th scope="row" className="text-left">{item.name}</th><td>{item.value}</td></tr>)}</tbody></table></div>
      </details>}
    </motion.div>
  );
}
