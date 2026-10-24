import { motion } from 'framer-motion';
import { cn } from '../../utils/helpers';

interface Props {
  current: number | null;
  previous: number | null;
  change: number | null;
  status: 'Good' | 'Warning' | 'At Risk' | 'Not recorded';
}

const statusColor = {
  Good: { text: 'text-ns-success', ring: 'var(--ns-success)' },
  Warning: { text: 'text-ns-warning', ring: 'var(--ns-warning)' },
  'At Risk': { text: 'text-ns-danger', ring: 'var(--ns-danger)' },
  'Not recorded': { text: 'text-ns-text-muted', ring: 'var(--ns-divider)' }
};

export default function AttendanceCard({ current, previous, change, status }: Props) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - ((current ?? 0) / 100) * circumference;
  const color = statusColor[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="neo-card p-6"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-ink">Attendance</h3>
        <p className="text-xs text-ink-faint">Overall attendance rate</p>
      </div>

      <div className="flex items-center gap-6">
        <div className="relative w-36 h-36">
          <svg width="144" height="144" viewBox="0 0 144 144" className="-rotate-90">
            <circle cx="72" cy="72" r={radius} fill="none" stroke="var(--ns-divider)" strokeWidth="12" />
            <motion.circle
              cx="72"
              cy="72"
              r={radius}
              fill="none"
              stroke={color.ring}
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: dashOffset }}
              transition={{ duration: 1.2, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-center text-xl font-extrabold text-ink">{current == null ? '—' : `${current}%`}</span>
            <span className={cn('text-xs font-semibold', color.text)}>{status}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-xs text-ink-faint">Current</p>
            <p className="text-lg font-bold text-ink">{current == null ? 'Not recorded' : `${current}%`}</p>
          </div>
          <div>
            <p className="text-xs text-ink-faint">Previous</p>
            <p className="text-lg font-bold text-ink">{previous == null ? '—' : `${previous}%`}</p>
          </div>
          <div>
            <p className="text-xs text-ink-faint">Change</p>
            <p className={cn('text-lg font-bold', change == null ? 'text-ns-text-muted' : change < 0 ? 'text-red-500' : 'text-emerald-600')}>
              {change == null ? '—' : `${change > 0 ? '+' : ''}${change}%`}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
