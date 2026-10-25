import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { RiskPrediction } from '../../types';
import { cn, riskColor } from '../../utils/helpers';
import { useAccessibility } from '../../context/AccessibilityContext';

interface Props {
  risk: RiskPrediction;
}

export default function RiskPredictionCard({ risk }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useAccessibility();
  if (!risk.id) {
    return (
      <section className="neo-card p-5 md:p-6">
        <h3 className="font-semibold text-ns-text-primary">Risk assessment</h3>
        <p className="mt-4 text-sm text-ns-text-secondary">{risk.explanation}</p>
        <p className="mt-3 text-xs text-ns-text-muted">
          A risk assessment will appear here when one has been generated from your recorded information.
        </p>
      </section>
    );
  }

  const color = riskColor(risk.risk_level);
  const score = risk.risk_score;
  const isMachineLearningPrediction = risk.model_version.startsWith('ml_');

  return (
    <section className="neo-card p-5 md:p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-ns-text-primary">Risk assessment</h3>
        <span
          className={cn('neo-chip border', risk.risk_level === 'HIGH'
            ? 'border-red-200 bg-red-50 text-ns-danger'
            : risk.risk_level === 'MEDIUM'
              ? 'border-amber-200 bg-amber-50 text-ns-warning'
              : 'border-emerald-200 bg-emerald-50 text-ns-success')}
        >
          {t(`risk.${risk.risk_level.toLowerCase()}`)}
        </span>
      </div>

      <div className="mb-4">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm text-ns-text-secondary">{t('risk.score')}</span>
          <span className="text-2xl font-semibold text-ns-text-primary">
            {score}<span className="ml-1 text-sm font-normal text-ns-text-muted">/100</span>
          </span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded bg-ns-divider" role="img" aria-label={`${t('risk.score')}: ${score} out of 100`}>
          <div className="h-full" style={{ width: `${score}%`, backgroundColor: color }} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ns-text-muted">
          <span>Model: {risk.model_version}</span>
          <span>Updated: {new Date(risk.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      <div className="bg-ns-surface-secondary border border-ns-border p-4 rounded-lg mb-4">
        <p className="text-xs font-medium text-ns-text-secondary leading-relaxed">
          "{risk.explanation}"
        </p>
      </div>

      <aside className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-950">
        Prototype screening signal only—not a diagnosis or an automated decision. Some inputs may be estimated or defaulted when records are missing. {isMachineLearningPrediction && 'The classifier’s reported metrics come from an internal holdout split, not an independent evaluation on institutional outcomes. '}Review the evidence with a staff member before acting.
      </aside>

      <button
        onClick={() => setExpanded((v) => !v)}
        className="min-h-11 w-full flex items-center justify-center gap-1.5 py-2 text-sm font-semibold text-brand-800 hover:text-brand-700 transition-colors"
        aria-expanded={expanded}
        aria-controls="risk-factor-list"
      >
        {expanded ? 'Hide factors' : 'Show factors'}
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      <div id="risk-factor-list" hidden={!expanded}>
        <div className="pt-3 space-y-2 border-t border-ns-divider mt-2">
          {risk.factors.map((f, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-lg bg-white px-3 py-2 border border-ns-border"
            >
              <span className="text-[11px] font-semibold text-ns-text-primary flex items-center gap-2">
                <span aria-hidden="true"
                  className={cn(
                    'w-1.5 h-1.5 rounded-full shadow-[0_0_8px]',
                    f.direction === 'increase' ? 'bg-red-400 shadow-red-400/50' : 'bg-emerald-400 shadow-emerald-400/50'
                  )}
                />
                {f.factor} <span className="font-medium">({f.direction === 'increase' ? t('risk.increases') : t('risk.reduces')})</span>
              </span>
              <span
                className={cn(
                  'text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full border',
                  f.direction === 'increase' ? 'bg-red-50 text-ns-danger border-red-200' : 'bg-emerald-50 text-ns-success border-emerald-200'
                )}
              >
                {f.impact}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
