import { motion } from 'framer-motion';
import { TrendingDown, TrendingUp, Minus, Info } from 'lucide-react';
import type { LmsInterventionComparison } from '../../types';
import { cn } from '../../utils/helpers';

interface ProgressComparisonCardProps {
  comparison: LmsInterventionComparison;
  /** Optional title override, e.g. "Progress since referral" for advisors. */
  title?: string;
}

const directionStyles: Record<LmsInterventionComparison['direction'], string> = {
  IMPROVED: 'bg-emerald-50 text-ns-success',
  DECLINED: 'bg-red-50 text-ns-danger',
  MIXED: 'bg-amber-50 text-ns-warning',
  UNCHANGED: 'bg-ns-surface-secondary text-ns-text-secondary'
};

const changeStyles = {
  IMPROVED: 'text-ns-success',
  DECLINED: 'text-ns-danger',
  UNCHANGED: 'text-ns-text-muted'
} as const;

const ChangeIcon = ({ direction }: { direction: 'IMPROVED' | 'DECLINED' | 'UNCHANGED' }) => {
  if (direction === 'IMPROVED') return <TrendingUp size={14} />;
  if (direction === 'DECLINED') return <TrendingDown size={14} />;
  return <Minus size={14} />;
};

/**
 * Before-intervention vs current academic indicators.
 * The wording always states that correlation is not causation — the platform
 * reports recorded movement and never claims an intervention caused it.
 */
export default function ProgressComparisonCard({ comparison, title = 'Before intervention vs current' }: ProgressComparisonCardProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-ns-text-primary">{title}</h2>
          <p className="mt-1 text-xs text-ns-text-muted">
            Baseline recorded {new Date(comparison.baseline_captured_at).toLocaleString()} · {comparison.intervention_count} recorded intervention{comparison.intervention_count === 1 ? '' : 's'}
          </p>
        </div>
        <span className={cn('neo-chip', directionStyles[comparison.direction])}>{comparison.direction}</span>
      </div>

      <p className="mt-3 text-sm text-ns-text-secondary">{comparison.summary}</p>

      <div className="mt-4 overflow-x-auto">
        <table className="ns-table min-w-[560px]">
          <caption className="sr-only">Academic indicators before intervention compared with current records</caption>
          <thead>
            <tr>
              <th scope="col">Indicator</th>
              <th scope="col">Before intervention</th>
              <th scope="col">Current</th>
              <th scope="col">Change</th>
            </tr>
          </thead>
          <tbody>
            {comparison.changes.map((change) => (
              <tr key={change.metric}>
                <td>{change.label}</td>
                <td>{change.before}{change.unit}</td>
                <td className="font-semibold">{change.current}{change.unit}</td>
                <td>
                  <span className={cn('inline-flex items-center gap-1 font-semibold', changeStyles[change.direction])}>
                    <ChangeIcon direction={change.direction} />
                    {change.change > 0 ? '+' : ''}{change.change}{change.unit}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-ns-text-muted">
        <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
          Baseline risk {comparison.baseline_risk_level} · {comparison.baseline_risk_score}%
        </span>
        <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
          Current risk {comparison.current_risk_level} · {comparison.current_risk_score}%
        </span>
      </div>

      <p className="mt-3 flex items-start gap-2 text-xs text-ns-text-muted">
        <Info size={14} className="mt-0.5 shrink-0" />
        {comparison.caveat} This view reports recorded academic indicators only and does not evaluate whether an intervention caused the change.
      </p>
    </motion.section>
  );
}
