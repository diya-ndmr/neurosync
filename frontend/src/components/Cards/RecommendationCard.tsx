import { motion } from 'framer-motion';
import type { Recommendation } from '../../types';
import { cn } from '../../utils/helpers';

interface Props {
  recommendations: Recommendation[];
  onComplete: (id: string) => void;
  completingId?: string | null;
}

const categoryMeta = {
  academic: { label: 'Academic' },
  attendance: { label: 'Attendance' },
  wellbeing: { label: 'Wellbeing' },
  study: { label: 'Study' },
  administrative: { label: 'Administrative' }
};

export default function RecommendationCard({ recommendations, onComplete, completingId }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="neo-card p-5 md:p-6"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-ns-text-primary">Suggested next steps</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {recommendations.map((rec, i) => {
          const meta = categoryMeta[rec.category];
          const completed = rec.status === 'completed';
          return (
            <motion.div
              key={rec.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 + i * 0.07 }}
              className={cn(
                'flex items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-ns-surface-secondary',
                completed
                  ? 'bg-emerald-50 border-emerald-100'
                  : 'bg-white border-ns-border'
              )}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[9px] font-black uppercase tracking-[0.2em] text-ink-faint">
                    {meta.label}
                  </span>
                  <span
                    className={cn(
                      'text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full border',
                      rec.priority === 'high'
                        ? 'bg-red-400/10 text-red-400 border-red-400/20'
                        : rec.priority === 'medium'
                          ? 'bg-amber-400/10 text-amber-400 border-amber-400/20'
                          : 'bg-ns-surface-secondary text-ns-text-secondary border-ns-border'
                    )}
                  >
                    {rec.priority}
                  </span>
                </div>
                <p className="text-[13px] font-medium text-ns-text-primary leading-relaxed">{rec.message}</p>
              </div>
              <div className="shrink-0 pt-1">
                {completed ? (
                  <span className="text-xs font-medium text-ns-text-secondary">Completed</span>
                ) : (
                  <button
                    type="button"
                    disabled={completingId === rec.id}
                    aria-label={`Mark ${meta.label.toLowerCase()} suggestion complete`}
                    onClick={() => onComplete(rec.id)}
                    className="min-h-11 px-2 text-xs font-medium text-brand-800 hover:underline"
                  >
                    Mark complete
                  </button>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
