import { motion } from 'framer-motion';

export default function LoadingState({ label = 'Loading your data…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.4, ease: 'linear' }}
        className="w-12 h-12 rounded-full border-4 border-brand-200 border-t-brand-500"
      />
      <motion.p
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ repeat: Infinity, duration: 2 }}
        className="text-sm text-ink-faint font-medium"
      >
        {label}
      </motion.p>
    </div>
  );
}

