import { motion } from 'framer-motion';
import { ArrowRight, CalendarDays, HeartPulse, LifeBuoy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { greeting } from '../../utils/helpers';
import { useAuth } from '../../context/AuthContext';
import type { StudentProfile } from '../../types';

interface Props {
  student?: StudentProfile;
  academicAverage: number | null;
  academicTrend: 'improving' | 'declining' | 'stable';
  onRequestSupport: () => void;
}

export default function WelcomeCard({
  student,
  academicAverage,
  academicTrend,
  onRequestSupport
}: Props) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const name = user?.name || student?.first_name || 'there';
  const firstName = name.split(' ')[0];
  const summary = academicAverage === null
    ? 'Academic results will appear here when recorded.'
    : `Average ${academicAverage}% · ${academicTrend === 'improving' ? 'improving' : academicTrend === 'declining' ? 'declining' : 'steady'} trend.`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card dashboard-welcome p-7 relative overflow-hidden"
    >
      <div className="relative z-10 grid gap-8 min-[900px]:grid-cols-[minmax(0,1fr)_240px] min-[900px]:items-center">
        <div className="max-w-2xl">
          <h1 className="mt-2 text-3xl md:text-4xl font-semibold text-white tracking-tight">
            {greeting()}, {firstName}.
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-white/75">
            {summary}
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row min-[900px]:flex-col">
          <button type="button" onClick={() => navigate('/student/recommendations')} className="dashboard-hero-action dashboard-hero-action-primary">
            <CalendarDays size={18} aria-hidden="true" />
            <span>Plan my week</span>
            <ArrowRight size={16} className="ml-auto" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => navigate('/student/wellbeing')} className="dashboard-hero-action dashboard-hero-action-secondary">
            <HeartPulse size={18} aria-hidden="true" />
            <span>Wellness check-in</span>
            <ArrowRight size={16} className="ml-auto" aria-hidden="true" />
          </button>
          <button type="button" onClick={onRequestSupport} className="dashboard-hero-support">
            <LifeBuoy size={15} aria-hidden="true" />
            <span>Request support</span>
          </button>
        </div>
      </div>
    </motion.div>
  );
}
