import { AlertTriangle, ClipboardCheck } from 'lucide-react';
import type { LmsStudentReview } from '../types';

type Risk = LmsStudentReview['risk'];
type Metrics = LmsStudentReview['metrics'];

interface RiskExplanationPanelProps {
  risk: Risk;
  metrics: Metrics;
  recommendations?: string[];
}

export default function RiskExplanationPanel({ risk, metrics, recommendations = [] }: RiskExplanationPanelProps) {
  const nextSteps = recommendations.length ? recommendations : [
    ...(metrics.missing_submissions > 0 ? ['Review the currently missing submissions with the student.'] : []),
    ...(metrics.late_submissions > 0 ? ['Discuss the late submissions and whether academic support would help.'] : []),
    ...(metrics.assessment_trend === 'declining' ? ['Discuss the recent assessment trend and available academic support.'] : []),
    ...(!metrics.missing_submissions && !metrics.late_submissions && metrics.assessment_trend !== 'declining'
      ? ['Review the cited indicators with the student and agree next steps in context.']
      : [])
  ];

  return (
    <section className="neo-card border-l-4 border-l-amber-500 p-5" aria-labelledby="risk-explanation-title">
      <div className="flex items-start gap-3">
        <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-700" />
        <div>
          <h2 id="risk-explanation-title" className="font-semibold text-ns-text-primary">Why was this student flagged?</h2>
          <p className="mt-1 text-sm text-ns-text-secondary">
            {risk.risk_level} risk · {risk.risk_score}% indicator score
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ns-text-muted">Evidence</h3>
          {risk.evidence.length ? (
            <ul className="mt-2 space-y-1.5">{risk.evidence.map((item) => <li key={item} className="text-sm text-ns-text-secondary">• {item}</li>)}</ul>
          ) : <p className="mt-2 text-sm text-ns-text-muted">No evidence details were supplied for this assessment.</p>}
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ns-text-muted">Data period</h3>
          <p className="mt-2 text-sm text-ns-text-secondary">Attendance: last 7 and 30 days. Assessment, submission, quiz and engagement indicators: current LMS data snapshot.</p>
          <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-ns-text-muted">Recommended next steps</h3>
          <ul className="mt-2 space-y-1.5">{nextSteps.map((step) => <li key={step} className="flex gap-2 text-sm text-ns-text-secondary"><ClipboardCheck size={15} className="mt-0.5 shrink-0 text-brand-700" />{step}</li>)}</ul>
        </div>
      </div>

      <p className="mt-4 border-t border-ns-border pt-3 text-xs font-medium text-ns-text-muted">This score is an indicator to support staff review, not a diagnosis or a decision about the student.</p>
    </section>
  );
}
