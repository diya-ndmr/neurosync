import { motion } from 'framer-motion';

interface ModulePerformanceCardProps {
  modules: { module: string; mark: number }[];
}

export default function ModulePerformanceCard({ modules }: ModulePerformanceCardProps) {
  return (
    <section className="neo-card h-full p-5 md:p-6" aria-labelledby="module-performance-heading">
      <div className="mb-5">
        <h2 id="module-performance-heading" className="text-lg font-semibold text-ns-text-primary">Module performance</h2>
        <p className="mt-1 text-xs text-ns-text-muted">Assessment averages</p>
      </div>
      {modules.length === 0 ? (
        <div className="chart-empty flex min-h-48 items-center justify-center rounded-xl border border-dashed border-ns-border px-4 text-center text-sm text-ns-text-muted">
          No module averages have been recorded yet.
        </div>
      ) : (
        <>
          <div className="mb-5 flex justify-between border-b border-dashed border-ns-border pb-2 text-[10px] font-semibold text-ns-text-muted" aria-hidden="true">
            <span>0%</span><span>50%</span><span>100%</span>
          </div>
          <div className="space-y-5">
          {modules.slice(0, 5).map((module, index) => {
            const mark = Math.min(100, Math.max(0, module.mark));
            return (
              <motion.div
                key={module.module}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="module-progress"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-ns-text-primary">{module.module}</p>
                  <p className="shrink-0 rounded-md bg-ns-primary-light px-2 py-1 text-xs font-bold text-ns-primary-dark">{module.mark}%</p>
                </div>
                <div className="module-progress-track" role="meter" aria-label={`${module.module} latest recorded assessment average`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={mark}>
                  <div className="module-progress-fill" style={{ width: `${mark}%` }} />
                </div>
              </motion.div>
            );
          })}
          </div>
        </>
      )}
      {modules.length > 5 && (
        <p className="mt-4 text-xs text-ns-text-muted">Showing 5 of {modules.length} modules. View Academics for the full breakdown.</p>
      )}
    </section>
  );
}
