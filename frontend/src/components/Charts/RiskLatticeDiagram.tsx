import { motion } from 'framer-motion';
import { ArrowDown, ArrowUp, Layers3 } from 'lucide-react';

interface RiskLatticeDiagramProps {
  data: { name: string; value: number }[];
}

const bands = [
  { name: 'LOW', range: '75–100%', action: 'Maintain momentum', tone: 'bg-emerald-50 border-emerald-200 text-emerald-800', dot: 'bg-emerald-500' },
  { name: 'MEDIUM', range: '51–74%', action: 'Monitor closely', tone: 'bg-amber-50 border-amber-200 text-amber-800', dot: 'bg-amber-500' },
  { name: 'HIGH', range: '0–50%', action: 'Prioritise support', tone: 'bg-red-50 border-red-200 text-red-800', dot: 'bg-red-500' }
];

export default function RiskLatticeDiagram({ data }: RiskLatticeDiagramProps) {
  const counts = new Map(data.map((item) => [item.name.toUpperCase(), item.value]));
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="neo-card p-5 md:p-6"
      aria-labelledby="risk-lattice-title"
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-lg bg-brand-50 flex items-center justify-center text-brand-800 border border-brand-100">
          <Layers3 size={20} />
        </div>
        <div>
          <h3 id="risk-lattice-title" className="font-semibold text-ns-text-primary">Academic risk lattice</h3>
          <p className="text-xs text-ns-text-muted mt-0.5">Mark bands used by NeuroSync triage</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_1fr]" role="list" aria-label="Academic risk lattice">
        <div className="relative flex flex-col justify-between gap-3 rounded-lg border border-ns-border bg-ns-surface-secondary/50 p-4">
          <p className="text-[11px] font-bold uppercase tracking-wider text-ns-text-muted">Academic mark axis</p>
          <div className="flex items-center justify-between text-xs text-ns-text-secondary"><span>100%</span><span>75%</span><span>51%</span><span>0%</span></div>
          <div className="h-2 rounded-full bg-gradient-to-r from-emerald-500 via-amber-400 to-red-500" aria-hidden="true" />
          <p className="text-xs text-ns-text-muted">Higher marks move upward through the lattice.</p>
        </div>
        <div className="flex items-center justify-center text-ns-text-muted"><ArrowUp className="hidden md:block" size={22} aria-hidden="true" /><ArrowDown className="md:hidden" size={22} aria-hidden="true" /></div>
        <div className="space-y-3">
        {bands.map((band) => {
          const count = counts.get(band.name) ?? 0;
          const share = total ? Math.round((count / total) * 100) : 0;
          return (
            <div key={band.name} className={`relative flex items-center gap-3 rounded-lg border p-3 ${band.tone}`} role="listitem">
              <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-4 border-white shadow-sm ${band.dot}`}><span className="text-base font-bold text-white">{count}</span></div>
              <div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><p className="text-xs font-bold tracking-wide">{band.name}</p><p className="text-sm font-bold">{share}%</p></div><p className="mt-1 text-[11px] font-medium">{band.range} · {band.action}</p></div>
            </div>
          );
        })}
        </div>
      </div>
      <p className="mt-4 text-xs text-ns-text-muted">Each node is a decision state: the mark threshold determines the label, while the action cue keeps triage understandable.</p>
    </motion.section>
  );
}