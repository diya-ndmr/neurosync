import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '../../utils/helpers';
import type { ReactNode } from 'react';

interface NeoButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: ReactNode;
}

const variantClasses = {
  primary: 'neo-btn',
  secondary:
    'rounded-lg bg-white border border-ns-border text-brand-800 font-semibold transition-colors hover:bg-ns-surface-secondary active:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
  ghost:
    'rounded-lg text-ns-text-secondary font-medium hover:text-brand-800 hover:bg-brand-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
  danger:
    'rounded-lg bg-ns-danger text-white font-semibold transition-colors hover:bg-red-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ns-danger focus-visible:ring-offset-2',
  success:
    'rounded-lg bg-ns-success text-white font-semibold transition-colors hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ns-success focus-visible:ring-offset-2'
};

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-5 py-2.5 text-sm',
  lg: 'px-7 py-3.5 text-base'
};

export default function NeoButton({
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  children,
  disabled,
  ...props
}: NeoButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
      disabled={disabled || loading}
      className={cn(variantClasses[variant], sizeClasses[size], className)}
      {...props}
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          Loading…
        </span>
      ) : (
        children
      )}
    </motion.button>
  );
}

