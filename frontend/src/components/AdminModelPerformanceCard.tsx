import { useEffect, useState } from 'react';
import { AlertTriangle, BrainCircuit } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface ModelPerformance {
  model_name: string | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  evaluated_at: string | null;
  training_data_source: string;
  validation_status: string;
}

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg border border-ns-border bg-white p-3">
      <p className="text-xs text-ns-text-muted">{label}</p>
      <p className="mt-1 text-lg font-bold text-ns-text-primary">{value == null ? 'Not recorded' : new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 }).format(value)}</p>
    </div>
  );
}

export default function AdminModelPerformanceCard() {
  const { token } = useAuth();
  const [data, setData] = useState<ModelPerformance | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.get<ModelPerformance>('/admin/model-performance', token || undefined)
      .then((result) => { if (active) setData(result); })
      .catch((requestError) => { if (active) setError(requestError instanceof Error ? requestError.message : 'Model evaluation metrics are unavailable.'); });
    return () => { active = false; };
  }, [token]);

  return (
    <section className="neo-card p-5" aria-labelledby="model-performance-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-brand-100 bg-brand-50 text-brand-800"><BrainCircuit size={20} /></div>
          <div>
            <h2 id="model-performance-heading" className="font-bold text-ink">Model Performance</h2>
            <p className="text-xs text-ink-soft">{data?.model_name?.replace(/_/g, ' ') ?? 'Prototype model'}</p>
          </div>
        </div>
        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">Prototype · not validated</span>
      </div>
      {error ? <p role="alert" className="mt-4 text-sm text-ns-danger">{error}</p> : data ? (
        <>
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Metric label="Precision (weighted)" value={data.precision} />
            <Metric label="Recall (weighted)" value={data.recall} />
            <Metric label="F1-score (weighted)" value={data.f1_score} />
          </div>
          <div className="mt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-ink-soft">
            <p>Last evaluation: {data.evaluated_at ? new Date(data.evaluated_at).toLocaleString() : 'Not recorded'}</p>
            <p>Training data: {data.training_data_source}</p>
          </div>
        </>
      ) : <p className="mt-4 text-sm text-ink-soft">Loading evaluation metrics…</p>}
      <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <AlertTriangle size={17} className="mt-0.5 shrink-0" />
        <p>Real-world validation on student data is pending. Synthetic holdout results do not establish real-world performance.</p>
      </div>
    </section>
  );
}
