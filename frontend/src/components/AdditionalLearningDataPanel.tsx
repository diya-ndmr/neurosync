import type { LmsStudySession, SupplementaryAssessmentFeedback } from '../services/liveData';

interface Props {
  feedback: SupplementaryAssessmentFeedback[] | null;
  feedbackLoading: boolean;
  feedbackError: string | null;
  studySessions: LmsStudySession[] | null;
  studyLoading: boolean;
  studyError: string | null;
}

export default function AdditionalLearningDataPanel({
  feedback,
  feedbackLoading,
  feedbackError,
  studySessions,
  studyLoading,
  studyError,
}: Props) {
  return (
    <section className="neo-card space-y-6 p-6">
      <div>
        <h2 className="font-bold text-ink">Supplementary learning data</h2>
        <p className="mt-1 text-sm text-ink-soft">
          Imported feedback and question outcomes are shown as recorded. They are not a mastery assessment.
        </p>
      </div>

      <div>
        <h3 className="mb-3 text-sm font-bold text-ink">Assessment feedback and quiz questions</h3>
        <p className="mb-3 text-xs text-ink-faint">
          The source file does not include module names, assessment titles, marks, or dates for these records.
        </p>
        {feedbackLoading ? (
          <p className="text-sm text-ink-faint">Loading supplementary feedback…</p>
        ) : feedbackError ? (
          <p role="alert" className="text-sm text-ns-danger">{feedbackError}</p>
        ) : !feedback?.length ? (
          <p className="text-sm text-ink-faint">No supplementary assessment feedback or quiz results recorded.</p>
        ) : (
          <div className="space-y-3">
            {feedback.map((item) => (
              <article key={item.assessment_id} className="rounded-xl border border-brand-100/60 bg-white/60 p-4">
                <h4 className="text-sm font-bold text-ink">Assessment reference: {item.assessment_id}</h4>
                {item.feedback && <p className="mt-2 text-sm text-ink-soft">{item.feedback}</p>}
                {item.question_count > 0 && (
                  <>
                    <p className="mt-3 text-xs font-semibold text-ink-soft">
                      {item.correct_count} of {item.question_count} recorded answers correct
                    </p>
                    <ul className="mt-2 grid gap-1 text-xs text-ink-faint sm:grid-cols-2">
                      {item.questions.map((question) => (
                        <li key={question.question_id}>
                          {question.question_id}: {question.is_correct ? 'Correct' : 'Incorrect'}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </article>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="mb-3 text-sm font-bold text-ink">Study sessions</h3>
        {studyLoading ? (
          <p className="text-sm text-ink-faint">Loading study sessions…</p>
        ) : studyError ? (
          <p role="alert" className="text-sm text-ns-danger">{studyError}</p>
        ) : !studySessions?.length ? (
          <p className="text-sm text-ink-faint">No study sessions recorded.</p>
        ) : (
          <ul className="space-y-2">
            {studySessions.map((session) => (
              <li key={session.id} className="flex flex-wrap justify-between gap-2 rounded-lg bg-white/60 p-3 text-sm">
                <span className="font-medium text-ink">{new Date(session.created_at).toLocaleString()}</span>
                <span className="text-ink-soft">{session.duration_minutes} minutes · {session.subject}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
