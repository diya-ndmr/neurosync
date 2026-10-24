import { motion } from 'framer-motion';
import NeoButton from '../Buttons/NeoButton';
import { timeAgo } from '../../utils/helpers';

interface Props {
  moodScore: number | null;
  stressLevel: number | null;
  lastCheckin: string;
  onCheckin?: () => void;
}

export default function WellbeingCard({ moodScore, stressLevel, lastCheckin, onCheckin }: Props) {
  const moodLabel = moodScore == null ? 'Not recorded' : moodScore >= 8 ? 'Great' : moodScore >= 6 ? 'Good' : moodScore >= 4 ? 'Okay' : 'Low';
  const stressLabel = stressLevel == null ? 'Not recorded' : stressLevel >= 8 ? 'High' : stressLevel >= 5 ? 'Medium' : 'Low';

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="neo-card p-6"
    >
      <div className="mb-4">
        <h3 className="font-semibold text-ink">Wellbeing</h3>
        <p className="text-xs text-ink-faint">Recent mood and stress</p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-lg bg-ns-surface-secondary border border-ns-border p-4 text-center">
          <p className="mb-1 text-xs font-medium text-ns-text-secondary">Mood</p>
          <p className="text-2xl font-extrabold text-ink">
            {moodScore ?? '—'}
            {moodScore != null && <span className="text-sm text-ink-faint">/10</span>}
          </p>
          <p className="text-xs font-semibold text-emerald-600">{moodScore == null ? moodLabel : `${moodLabel} mood`}</p>
        </div>
        <div className="rounded-lg bg-ns-surface-secondary border border-ns-border p-4 text-center">
          <p className="mb-1 text-xs font-medium text-ns-text-secondary">Stress</p>
          <p className="text-2xl font-extrabold text-ink">
            {stressLevel ?? '—'}
            {stressLevel != null && <span className="text-sm text-ink-faint">/10</span>}
          </p>
          <p className="text-xs font-semibold text-amber-600">{stressLevel == null ? stressLabel : `${stressLabel} stress`}</p>
        </div>
      </div>

      <p className="text-xs text-ink-faint mb-4">{lastCheckin ? `Last check-in: ${timeAgo(lastCheckin)}` : 'No check-in recorded yet'}</p>

      <NeoButton variant="secondary" size="sm" className="w-full" onClick={onCheckin}>
        Complete Check-in
      </NeoButton>
    </motion.div>
  );
}
