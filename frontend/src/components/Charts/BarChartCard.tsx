import { motion } from 'framer-motion';
import { useId } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
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

export default function BarChartCard({
  title,
  subtitle,
  data,
  dataKey = 'value',
  color = 'var(--ns-primary)',
  index = 0
}: Props) {
  const gradientId = `bar-gradient-${useId().replace(/:/g, '')}`;
  const chartHeight = Math.max(250, Math.min(460, data.length * 52 + 52));

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.1 }}
      className="neo-card p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-ns-text-primary">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-ns-text-muted">{subtitle}</p>}
      </div>

      {data.length === 0 ? (
        <div className="chart-empty mt-4 flex h-64 items-center justify-center rounded-xl border border-dashed border-ns-border text-sm text-ns-text-muted">
          No recorded data
        </div>
      ) : (
        <div className="chart-frame mt-4 rounded-xl p-3" style={{ height: chartHeight }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 6, right: 34, left: 4, bottom: 4 }}
              barCategoryGap="32%"
            >
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={color} stopOpacity={0.72} />
                  <stop offset="100%" stopColor={color} stopOpacity={1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="4 6" stroke="var(--ns-divider)" vertical={true} horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 'dataMax']}
                tick={{ fill: 'var(--ns-text-muted)', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickCount={5}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={112}
                tick={{ fill: 'var(--ns-text-secondary)', fontSize: 11, fontWeight: 600 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value: string) => value.length > 17 ? `${value.slice(0, 16)}…` : value}
              />
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
                cursor={{ fill: 'rgb(var(--ns-primary-rgb) / 7%)' }}
              />
              <Bar dataKey={dataKey} fill={`url(#${gradientId})`} radius={[0, 8, 8, 0]} maxBarSize={24}>
                <LabelList dataKey={dataKey} position="right" fill="var(--ns-text-secondary)" fontSize={10} fontWeight={700} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {data.length > 0 && <details className="mt-3 text-sm">
        <summary className="min-h-11 cursor-pointer py-3 font-semibold text-brand-800 focus-visible:outline-2 focus-visible:outline-offset-2">View chart data as a table</summary>
        <div className="overflow-x-auto"><table className="ns-table"><caption className="sr-only">{title} chart values</caption><thead><tr><th scope="col">Category</th><th scope="col">{dataKey}</th></tr></thead><tbody>{data.map((item) => <tr key={item.name}><th scope="row" className="text-left">{item.name}</th><td>{item.value}</td></tr>)}</tbody></table></div>
      </details>}
    </motion.div>
  );
}
