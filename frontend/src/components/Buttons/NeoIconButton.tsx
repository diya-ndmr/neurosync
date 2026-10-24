import { motion, type HTMLMotionProps } from 'framer-motion';
import type { ReactNode } from 'react';
import { cn } from '../../utils/helpers';

interface NeoIconButtonProps extends HTMLMotionProps<'button'> {
  label: string;
  badge?: number;
  children: ReactNode;
}

export default function NeoIconButton({ label, badge, children, className, ...props }: NeoIconButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      aria-label={label}
      title={label}
      className={cn(
        'relative w-11 h-11 rounded-lg flex items-center justify-center text-ns-text-secondary bg-white border border-ns-border hover:text-brand-800 hover:bg-ns-surface-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className
      )}
      {...props}
    >
      {children}
      {badge !== undefined && badge > 0 && (
        <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-ns-danger text-white text-[10px] font-bold flex items-center justify-center">
          {badge > 9 ? '9+' : badge}
        </span>
      )}
    </motion.button>
  );
}

