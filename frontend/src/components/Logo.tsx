import { motion } from 'framer-motion';
import { cn } from '../utils/helpers';
import logoImage from '../assets/neurosync-logo/neurosync-logo.jpg';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  inverse?: boolean;
  className?: string;
}

const sizeMap = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-14 h-14',
  xl: 'w-24 h-24'
};

const textSizeMap = {
  sm: 'text-base',
  md: 'text-xl',
  lg: 'text-2xl',
  xl: 'text-4xl'
};

export default function Logo({ size = 'md', showText = true, inverse = false, className }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <motion.div
        whileHover={{ rotate: 6, scale: 1.05 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className={cn(
          'rounded-lg shadow-sm overflow-hidden shrink-0 bg-white ring-1 ring-brand-100',
          sizeMap[size]
        )}
      >
        <img
          src={logoImage}
          alt="NeuroSync logo"
          className="w-full h-full object-cover"
        />
      </motion.div>
      {showText && (
        <div className="leading-tight">
          <span
            className={cn(
              'font-extrabold tracking-tight',
              inverse ? 'text-brand-300' : 'text-brand-800',
              textSizeMap[size]
            )}
          >
            Neuro
          </span>
          <span
            className={cn(
              'font-extrabold tracking-tight',
              inverse ? 'text-brand-200' : 'text-brand-700',
              textSizeMap[size]
            )}
          >
            Sync
          </span>
          {size === 'lg' || size === 'xl' ? (
            <p className="text-[11px] font-medium text-ink-faint tracking-wide uppercase">
              University Intelligence
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}

