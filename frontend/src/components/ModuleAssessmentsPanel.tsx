import { useMemo, useState } from 'react';
import type { LmsAssessmentRow } from '../services/liveData';

const markColour = (mark: number) => (mark >= 75 ? 'text-emerald-600' : mark >= 50 ? 'text-amber-600' : 'text-red-500');

interface Props {
  assessments: LmsAssessmentRow[];
}

export default function ModuleAssessmentsPanel({ assessments }: Props) {
  const modules = useMemo(() => {
    const map = new Map<string, { key: string; name: string; code: string; rows: LmsAssessmentRow[] }>();
    for (const a of assessments) {
      const key = a.module_id ?? a.module_code ?? a.module;
      if (!map.has(key)) map.set(key, { key, name: a.module, code: a.module_code, rows: [] });
      map.get(key)!.rows.push(a);
    }
    return [...map.values()].map((m) => ({
      ...m,
      average: m.rows.reduce((sum, r) => sum + r.mark, 0) / m.rows.length,
    }));
  }, [assessments]);
  const [selected, setSelected] = useState<string | null>(null);
  const active = modules.find((m) => m.key === selected);

  if (modules.length === 0) return <p className="text-sm text-ink-faint">No assessments recorded yet.</p>;

  if (active) {
    const types = [...new Set(active.rows.map((r) => r.assessment_type))];
    return (
      <div className="space-y-4">
        <button type="button" onClick={() => setSelected(null)} className="text-sm font-semibold text-brand-700 underline">
          ← All modules
        </button>
        <div>
          <h3 className="text-lg font-bold text-ink">{active.name}</h3>
          <p className="text-xs text-ink-faint">
            {active.code} · {active.rows.length} assessments · average {active.average.toFixed(1)}%
          </p>
        </div>
        {types.map((type) => (
          <section key={type} aria-label={type} className="space-y-2">
            <h4 className="text-sm font-bold uppercase tracking-wide text-ink-soft">{type === 'Quiz' ? 'Quizzes' : `${type}s`}</h4>
            {active.rows
              .filter((r) => r.assessment_type === type)
              .map((r) => (
                <div key={r.id} className="rounded-2xl border border-brand-100/60 bg-white/60 p-3.5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-bold text-ink">{r.title ?? `${r.assessment_type}`}</p>
                      <p className="text-xs text-ink-faint">
                        {new Date(r.assessment_date).toLocaleDateString()}
                        {r.topic ? ` · ${r.topic}` : ''}
                        {r.status ? ` · ${r.status}` : ''}
                      </p>
                    </div>
                    <p className={`text-lg font-extrabold ${markColour(r.mark)}`}>
                      {r.mark}
                      {r.max_score ? `/${r.max_score}` : '%'}
                    </p>
                  </div>
                  <p className="mt-2 text-sm text-ink-soft">
                    <span className="font-semibold">Feedback: </span>
                    {r.feedback || 'No feedback recorded yet.'}
                  </p>
                </div>
              ))}
          </section>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {modules.map((m) => (
        <button
          key={m.key}
          type="button"
          onClick={() => setSelected(m.key)}
          className="flex w-full items-center justify-between rounded-2xl border border-brand-100/60 bg-white/60 p-3.5 text-left hover:border-brand-300"
        >
          <div>
            <p className="text-sm font-bold text-ink">{m.name}</p>
            <p className="text-xs text-ink-faint">
              {m.code} · {m.rows.length} assessments · view quizzes, exams and feedback
            </p>
          </div>
          <p className={`text-lg font-extrabold ${markColour(m.average)}`}>{m.average.toFixed(1)}%</p>
        </button>
      ))}
    </div>
  );
}
