import { motion } from 'framer-motion';
import { greeting } from '../../utils/helpers';
import { useAuth } from '../../context/AuthContext';
import type { StudentProfile } from '../../types';

interface Props {
  student?: StudentProfile;
  academicStatus?: string;
}

export default function WelcomeCard({ student, academicStatus = 'Good standing' }: Props) {
  const { user } = useAuth();
  const name = user?.name || student?.first_name || 'there';
  const programme = student?.programme || 'Bachelor of Information Technology';
  const year = student?.year_level ?? 2;

  const isAtRisk = false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-7 relative overflow-hidden"
    >
      <div className="relative">
        <p className="text-sm font-medium text-ink-faint">{greeting()},</p>
        <h1 className="mt-1 text-2xl md:text-3xl font-semibold text-ink tracking-tight">
          {name}
        </h1>

        <div className="mt-4 flex flex-wrap gap-3">
          <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
            {programme}
          </span>
          <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
            {year > 0 ? `Year ${year}` : 'Year not provided'}
          </span>
          <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
            Academic status: {academicStatus === 'Good standing' && isAtRisk ? 'Needs attention' : academicStatus}
          </span>
        </div>

        <p className="mt-4 text-sm text-ink-soft max-w-xl">
          Your university academic overview.
        </p>
      </div>
    </motion.div>
  );
}
