interface ImportedStudent {
  student_id: string;
  name: string;
  faculty: string;
  risk_level: string;
  attendance_percent: string;
  average_mark: string;
  last_lms_login: string;
  assigned_advisor: string;
  email?: string;
  phone_number?: string;
}

interface ImportedReferral {
  student_id: string;
  referral_id: string;
  advisor_id: string;
  risk_level: string;
  reason: string;
  urgency: string;
  status: string;
  created_date: string;
  next_follow_up: string;
}

interface ImportedIntervention {
  student_id: string;
  intervention_id: string;
  referral_id: string;
  strategy: string;
  start_date: string;
  review_date: string;
  status: string;
  follow_up_due: string;
}

interface ImportedAction {
  student_id: string;
  action_id: string;
  referral_id: string;
  action_type: string;
  due_date: string;
  status: string;
  priority: string;
}

interface ImportedSupportRequest {
  student_id: string;
  request_id: string;
  request_type: string;
  submitted_date: string;
  status: string;
  assigned_advisor: string;
}

export interface ImportedDemoDataset {
  label: string;
  counts: {
    students: number;
    combined_summaries: number;
    referrals: number;
    interventions: number;
    actions: number;
    support_requests: number;
  };
  students: ImportedStudent[];
  referrals: ImportedReferral[];
  interventions: ImportedIntervention[];
  actions: ImportedAction[];
  support_requests: ImportedSupportRequest[];
}

interface Props {
  dataset: ImportedDemoDataset | null;
}

const sectionClass = 'rounded-lg border border-ns-border bg-white';
const summaryClass = 'cursor-pointer list-none px-4 py-3 text-sm font-semibold text-ns-text-primary';

export default function ImportedDemoDatasetSection({ dataset }: Props) {
  if (!dataset) return null;

  const { counts } = dataset;
  const referralsWithStatus = (status: string) => dataset.referrals.filter(
    (referral) => referral.status.trim().toLowerCase() === status.toLowerCase(),
  ).length;
  const countOpen = (status: string) => status.trim().toLowerCase() === 'open';
  const activeInterventions = dataset.interventions.filter(
    (intervention) => intervention.status.trim().toLowerCase() === 'active',
  ).length;
  const openActions = dataset.actions.filter((action) => countOpen(action.status)).length;
  const openSupportRequests = dataset.support_requests.filter((request) => countOpen(request.status)).length;

  return (
    <section className="neo-card space-y-4 p-5 md:p-6" aria-labelledby="imported-demo-data-title">
      <div>
        <h2 id="imported-demo-data-title" className="font-bold text-ns-text-primary">Imported demo dataset</h2>
        <p className="mt-1 text-xs text-ns-text-secondary">{dataset.label}. Read-only source summaries; these records do not alter the live LMS, risk scores, or native case workflow.</p>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-ns-text-primary">Imported workflow status</h3>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          <Count label="New referrals" value={referralsWithStatus('New')} />
          <Count label="Awaiting response" value={referralsWithStatus('Awaiting response')} />
          <Count label="Resolved referrals" value={referralsWithStatus('Resolved')} />
          <Count label="Active interventions" value={activeInterventions} />
          <Count label="Open advisor actions" value={openActions} />
          <Count label="Open support requests" value={openSupportRequests} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <Count label="Students" value={counts.students} />
        <Count label="Combined summaries" value={counts.combined_summaries} />
        <Count label="Referrals" value={counts.referrals} />
        <Count label="Interventions" value={counts.interventions} />
        <Count label="Advisor actions" value={counts.actions} />
        <Count label="Support requests" value={counts.support_requests} />
      </div>

      <div className="space-y-2">
        <details className={sectionClass}>
          <summary className={summaryClass}>Student summaries ({dataset.students.length})</summary>
          <div className="max-h-80 overflow-auto border-t border-ns-divider">
            <table className="ns-table min-w-[760px]">
              <thead><tr><th>Student</th><th>Faculty</th><th>Risk band</th><th>Attendance</th><th>Average mark</th>              <th>Advisor</th><th>Contact</th></tr></thead>
              <tbody>{dataset.students.map((student) => <tr key={student.student_id}>
                <td>{student.name} · {student.student_id}</td><td>{student.faculty}</td><td>{student.risk_level}</td>
                <td>{student.attendance_percent}%</td><td>{student.average_mark}%</td><td>{student.assigned_advisor}</td>
                              <td className="whitespace-nowrap">
                                {student.email && <a className="mr-3 text-brand-800 underline" href={`mailto:${student.email}?subject=${encodeURIComponent('Support check-in')}`}>Email</a>}
                                {student.phone_number && <><a className="mr-2 text-brand-800 underline" href={`tel:${student.phone_number}`}>Call {student.phone_number}</a>
                                <button type="button" className="text-xs underline" onClick={() => void navigator.clipboard?.writeText(student.phone_number ?? '')}>Copy</button></>}
                              </td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>

        <details className={sectionClass} open>
          <summary className={summaryClass}>Referrals ({dataset.referrals.length})</summary>
          <div className="max-h-80 overflow-auto border-t border-ns-divider">
            <table className="ns-table min-w-[760px]">
              <thead><tr><th>Referral</th><th>Student</th><th>Risk</th><th>Urgency</th><th>Status</th><th>Reason</th></tr></thead>
              <tbody>{dataset.referrals.map((referral) => <tr key={referral.referral_id}>
                <td>{referral.referral_id}</td><td>{referral.student_id}</td><td>{referral.risk_level}</td>
                <td>{referral.urgency}</td><td>{referral.status}</td><td>{referral.reason}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>

        <details className={sectionClass}>
          <summary className={summaryClass}>Interventions ({dataset.interventions.length})</summary>
          <div className="max-h-80 overflow-auto border-t border-ns-divider">
            <table className="ns-table min-w-[760px]">
              <thead><tr><th>Intervention</th><th>Student</th><th>Strategy</th><th>Status</th><th>Review</th><th>Follow-up</th></tr></thead>
              <tbody>{dataset.interventions.map((intervention) => <tr key={intervention.intervention_id}>
                <td>{intervention.intervention_id}</td><td>{intervention.student_id}</td><td>{intervention.strategy}</td>
                <td>{intervention.status}</td><td>{intervention.review_date || 'Not set'}</td><td>{intervention.follow_up_due || 'Not set'}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>

        <details className={sectionClass}>
          <summary className={summaryClass}>Advisor actions ({dataset.actions.length})</summary>
          <div className="max-h-80 overflow-auto border-t border-ns-divider">
            <table className="ns-table min-w-[640px]">
              <thead><tr><th>Action</th><th>Student</th><th>Type</th><th>Status</th><th>Priority</th><th>Due</th></tr></thead>
              <tbody>{dataset.actions.map((action) => <tr key={action.action_id}>
                <td>{action.action_id}</td><td>{action.student_id}</td><td>{action.action_type}</td>
                <td>{action.status}</td><td>{action.priority}</td><td>{action.due_date || 'Not set'}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>

        <details className={sectionClass}>
          <summary className={summaryClass}>Support request summaries ({dataset.support_requests.length})</summary>
          <div className="max-h-80 overflow-auto border-t border-ns-divider">
            <table className="ns-table min-w-[640px]">
              <thead><tr><th>Request</th><th>Student</th><th>Type</th><th>Status</th><th>Submitted</th><th>Advisor</th></tr></thead>
              <tbody>{dataset.support_requests.map((request) => <tr key={request.request_id}>
                <td>{request.request_id}</td><td>{request.student_id}</td><td>{request.request_type}</td>
                <td>{request.status}</td><td>{request.submitted_date}</td><td>{request.assigned_advisor}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>
      </div>
    </section>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3">
    <p className="text-xs text-ns-text-muted">{label}</p>
    <p className="mt-1 text-xl font-semibold text-brand-800">{value}</p>
  </div>;
}
