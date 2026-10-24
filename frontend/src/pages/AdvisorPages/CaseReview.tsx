import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Clock3, Mail, Plus, Send, Shield, Sparkles } from 'lucide-react';
import NeoButton from '../../components/Buttons/NeoButton';
import ProgressComparisonCard from '../../components/Cards/ProgressComparisonCard';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { LmsIntervention, LmsInterventionComparison, LmsReferral, LmsStudentReview } from '../../types';
import { riskBg } from '../../utils/helpers';

interface Suggestion { strategy: string; reason: string }
interface EventItem { event_type: string; summary: string; occurred_at: string }
interface CaseDetail {
  referral: LmsReferral;
  review: LmsStudentReview;
  recommendations: Suggestion[];
  interventions: LmsIntervention[];
  timeline: EventItem[];
  comparison: LmsInterventionComparison | null;
  advisor_notes?: { note_id: string; note: string; created_at: string }[];
  communications?: { message_id: string; subject: string; delivery_status: string; sent_at: string | null; body: string }[];
  meetings?: { meeting_id: string; meeting_at: string; purpose: string; status: string; advisor_notes: string | null }[];
}

const strategies = [
  'Academic Advisor Check-In', 'Lecturer Consultation', 'Academic Planning Session', 'Time Management Support',
  'Study Skills Support', 'Attendance Support', 'Assessment Recovery Plan', 'Peer Tutoring Referral',
  'Tutoring / Academic Support Referral', 'Learning Resource Guidance', 'Student Support Services Referral', 'Follow-Up Monitoring', 'Engagement Check-In'
];

export default function CaseReview() {
  const { referralId = '' } = useParams();
  const { token } = useAuth();
  const { showToast } = useToast();
  const [data, setData] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [strategy, setStrategy] = useState(strategies[0]);
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [followUpDate, setFollowUpDate] = useState('');
  const [reviewDate, setReviewDate] = useState('');
  const [privateNote, setPrivateNote] = useState('');
  const [subject, setSubject] = useState('A NeuroSync academic support check-in');
  const [body, setBody] = useState('Hello,\n\nWe have noticed some recent changes in your academic engagement and would like to check in with you. We would be glad to arrange a short meeting to discuss how things are going and whether any academic support may be helpful.\n\nPlease let us know a time that works for you.\n\nKind regards,\nAcademic Advising');
  const [draftId, setDraftId] = useState('');
  const [draftedByAi, setDraftedByAi] = useState(false);
  const [outcome, setOutcome] = useState('STABLE');
  const [meetingAt, setMeetingAt] = useState('');
  const [meetingPurpose, setMeetingPurpose] = useState('Academic support check-in');

  const load = async () => {
    try {
      const result = await api.get<CaseDetail>(`/workflow/advisor/referrals/${referralId}`, token || undefined);
      setData(result);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not load referral');
    }
  };
  useEffect(() => { void load(); }, [referralId, token]);

  const action = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError('');
    try { await fn(); await load(); showToast('Action completed and case details refreshed.'); }
    catch (requestError) { const message = requestError instanceof Error ? requestError.message : 'Action failed'; setError(message); showToast(message, 'error'); }
    finally { setBusy(false); }
  };

  if (error && !data) return <div role="alert" className="neo-card p-6 text-ns-danger">{error}</div>;
  if (!data) return <div className="py-12 text-center text-sm text-ns-text-muted">Loading referral…</div>;

  const { referral, review } = data;
  const createStrategy = (selectedStrategy: string, decision: 'ACCEPT' | 'MODIFY' | 'CHOOSE_DIFFERENT' | 'DISMISS', selectedReason: string) => action(() => api.post(`/workflow/advisor/referrals/${referralId}/strategies/decision`, {
    strategy: selectedStrategy,
    decision,
    reason: selectedReason || 'Selected by advisor after reviewing the available LMS evidence.',
    advisor_notes: notes || null,
    review_date: reviewDate || null,
    follow_up_date: followUpDate || null
  }, token || undefined));

  return (
    <div className="space-y-5">
      <Link to="/advisor/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-brand-800"><ArrowLeft size={16} /> Advisor queue</Link>
      {error && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-ns-danger">{error}</div>}
      <section className="neo-card p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-xs font-semibold uppercase text-ns-text-muted">Referral {referral.referral_id}</p><h1 className="mt-1 text-2xl font-bold">{review.student.name}</h1><p className="mt-1 text-sm text-ns-text-secondary">{review.student.student_id} · {review.student.programme} · Year {review.student.year_of_study}</p><a className="text-sm text-brand-800" href={`mailto:${review.student.institutional_email}`}>{review.student.institutional_email}</a></div>
          <div className="flex flex-wrap gap-2"><span className={`neo-chip ${riskBg(referral.risk_level as 'LOW' | 'MEDIUM' | 'HIGH')}`}>{referral.risk_level} · {referral.risk_score}%</span><span className="neo-chip bg-brand-50 text-brand-800">{referral.status.replace(/_/g, ' ')}</span></div>
        </div>
        <div className="mt-4 rounded-lg border border-ns-border bg-ns-surface-secondary p-4"><p className="text-xs font-semibold uppercase text-ns-text-muted">Lecturer referral</p><p className="mt-1 text-sm">{referral.reason}</p>{referral.lecturer_notes && <p className="mt-2 text-sm text-ns-text-secondary">Shared lecturer notes: {referral.lecturer_notes}</p>}</div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3"><Metric label="Attendance" value={`${review.metrics.attendance}%`} /><Metric label="Assessment average" value={`${review.metrics.academic_average}%`} /><Metric label="Submission rate" value={`${review.metrics.submission_rate}%`} /><Metric label="Engagement" value={`${review.metrics.engagement_score}/100`} /></div>
      </section>

      <section className="neo-card p-5"><h2 className="font-semibold">Academic evidence</h2><ul className="mt-3 space-y-2">{review.risk.evidence.map((item) => <li key={item} className="text-sm text-ns-text-secondary">• {item}</li>)}</ul><p className="mt-3 text-xs text-ns-text-muted">The data describes academic indicators and does not establish personal circumstances or causation.</p></section>

      <section className="neo-card p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">AI-assisted support suggestions</h2><p className="text-xs text-ns-text-muted">Suggestions only. You make the final intervention decision.</p></div><NeoButton variant="secondary" size="sm" onClick={() => void action(() => api.get(`/workflow/advisor/referrals/${referralId}/strategies`, token || undefined))}><Sparkles size={15} className="mr-1.5 inline" />Refresh suggestions</NeoButton></div>
        <div className="mt-4 space-y-3">{data.recommendations.length ? data.recommendations.map((suggestion, index) => <div key={`${suggestion.strategy}-${index}`} className="rounded-lg border border-ns-border bg-white p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-semibold">{suggestion.strategy}</h3><p className="mt-1 text-sm text-ns-text-secondary">{suggestion.reason}</p></div><span className="neo-chip bg-brand-50 text-brand-800">Suggested</span></div><div className="mt-3 flex flex-wrap gap-2"><NeoButton size="sm" loading={busy} onClick={() => void createStrategy(suggestion.strategy, 'ACCEPT', suggestion.reason)}><Check size={14} className="mr-1 inline" />Accept</NeoButton><NeoButton size="sm" variant="secondary" loading={busy} onClick={() => { setStrategy(suggestion.strategy); setReason(suggestion.reason); setCustomOpen(true); }}>Modify</NeoButton><select aria-label="Choose alternative strategy" className="neo-input w-auto py-1.5 text-sm" value={strategy} onChange={(event) => setStrategy(event.target.value)}><option value="">Choose different strategy…</option>{strategies.map((item) => <option key={item}>{item}</option>)}</select><NeoButton size="sm" variant="secondary" loading={busy} onClick={() => void createStrategy(strategy, 'CHOOSE_DIFFERENT', suggestion.reason)}>Use selected</NeoButton><button className="px-3 py-1.5 text-sm font-medium text-ns-text-muted hover:text-ns-danger" onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/strategies/decision`, { strategy: suggestion.strategy, decision: 'DISMISS', reason: suggestion.reason }, token || undefined))}>Dismiss</button></div></div>) : <p className="text-sm text-ns-text-muted">No suggestions were triggered by the currently available academic evidence.</p>}</div>
        <button className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-800" onClick={() => setCustomOpen((value) => !value)}><Plus size={16} />Add custom strategy</button>
        {customOpen && <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3"><label className="text-sm">Strategy<input className="neo-input mt-1" value={strategy} onChange={(event) => setStrategy(event.target.value)} /></label><label className="text-sm">Reason<textarea className="neo-input mt-1" rows={2} value={reason} onChange={(event) => setReason(event.target.value)} /></label><label className="text-sm">Advisor notes<textarea className="neo-input mt-1" rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} /></label><label className="text-sm">Review date<input className="neo-input mt-1" type="date" value={reviewDate} onChange={(event) => setReviewDate(event.target.value)} /></label><label className="text-sm">Follow-up date<input className="neo-input mt-1" type="date" value={followUpDate} onChange={(event) => setFollowUpDate(event.target.value)} /></label><div className="flex items-end"><NeoButton loading={busy} onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/strategies/custom`, { strategy, reason, advisor_notes: notes || null, review_date: reviewDate || null, follow_up_date: followUpDate || null }, token || undefined))}>Create strategy</NeoButton></div></div>}
      </section>

      <section className="neo-card p-5"><h2 className="font-semibold">Intervention history</h2>
<label className="mt-3 block text-sm">Advisor outcome<select className="neo-input mt-1 w-fit" value={outcome} onChange={(event) => setOutcome(event.target.value)}>{['IMPROVING', 'STABLE', 'CONTINUED_SUPPORT_REQUIRED', 'NO_RESPONSE', 'REFERRED_TO_OTHER_SUPPORT', 'INTERVENTION_COMPLETED'].map((value) => <option key={value} value={value}>{value.replace(/_/g, ' ')}</option>)}</select></label>
<div className="mt-3 space-y-3">{data.interventions.map((item) => <div key={item.intervention_id} className="rounded-lg border border-ns-border p-4"><div className="flex flex-wrap justify-between gap-2"><strong>{item.strategy}</strong><span className="neo-chip bg-brand-50 text-brand-800">{item.status}</span></div><p className="mt-1 text-sm text-ns-text-secondary">{item.reason}</p><p className="mt-2 text-xs text-ns-text-muted">Started {new Date(item.date_started).toLocaleDateString()} · Follow-up {item.follow_up_date || 'not scheduled'}</p><div className="mt-3 flex flex-wrap gap-2"><select aria-label="Intervention status" className="neo-input w-auto py-1.5 text-sm" defaultValue={item.status} onChange={(event) => void action(() => api.patch(`/workflow/advisor/interventions/${item.intervention_id}`, { status: event.target.value, outcome: event.target.value === 'COMPLETED' ? outcome : undefined }, token || undefined))}>{['PLANNED', 'ACTIVE', 'FOLLOW_UP', 'COMPLETED', 'DISCONTINUED'].map((status) => <option key={status}>{status}</option>)}</select><button className="text-sm text-brand-800" onClick={() => void action(() => api.patch(`/workflow/advisor/interventions/${item.intervention_id}`, { status: 'FOLLOW_UP', follow_up_date: followUpDate || new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10) }, token || undefined))}>Schedule follow-up</button><button className="text-sm text-ns-success" onClick={() => void action(() => api.patch(`/workflow/advisor/interventions/${item.intervention_id}`, { status: 'COMPLETED', outcome }, token || undefined))}>Complete</button></div></div>)}</div></section>

      <section className="neo-card p-5"><h2 className="font-semibold">Contact student · mock institutional email</h2><p className="mt-1 text-xs text-ns-text-muted">No external delivery. Draft → advisor review → approval → simulated send.</p>
      <div className="mt-3"><NeoButton variant="secondary" size="sm" loading={busy} onClick={async () => { setBusy(true); try { const draft = await api.get<{ subject: string; body: string }>(`/workflow/advisor/referrals/${referralId}/email-suggestion`, token || undefined); setSubject(draft.subject); setBody(draft.body); setDraftedByAi(true); await load(); showToast('Message draft prepared. Review it before sending.'); } catch (requestError) { const message = requestError instanceof Error ? requestError.message : 'Could not generate draft'; setError(message); showToast(message, 'error'); } finally { setBusy(false); } }}><Sparkles size={15} className="mr-1.5 inline" />Draft from academic indicators</NeoButton></div>
      <label className="mt-3 block text-sm">To<input className="neo-input mt-1" readOnly value={review.student.institutional_email} /></label>
      <label className="mt-3 block text-sm">Subject<input className="neo-input mt-1" value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
      <label className="mt-3 block text-sm">Message<textarea className="neo-input mt-1" rows={6} value={body} onChange={(event) => setBody(event.target.value)} /></label>
      <div className="mt-3 flex flex-wrap gap-2">
        <NeoButton loading={busy} onClick={async () => { setBusy(true); try { const draft = await api.post<{ message_id: string }>('/workflow/advisor/referrals/' + referralId + '/email-drafts', { subject, body, drafted_by_ai: draftedByAi }, token || undefined); setDraftId(draft.message_id); await load(); showToast('Message draft saved.'); } catch (e) { const message = e instanceof Error ? e.message : 'Could not save draft'; setError(message); showToast(message, 'error'); } finally { setBusy(false); } }}><Mail size={15} className="mr-1.5 inline" />Save draft</NeoButton>
        {draftId && <NeoButton variant="secondary" loading={busy} onClick={() => void action(() => api.post(`/workflow/advisor/emails/${draftId}/approval`, { approve: true }, token || undefined))}><Send size={15} className="mr-1.5 inline" />Approve & mock-send</NeoButton>}
      </div>
      <div className="mt-4 space-y-2">{(data.communications || []).map((message) => <div key={message.message_id} className="rounded-lg border border-ns-border p-3 text-sm"><div className="flex justify-between gap-2"><strong>{message.subject}</strong><span className="neo-chip bg-brand-50 text-brand-800">{message.delivery_status}</span></div><p className="mt-1 whitespace-pre-wrap text-ns-text-secondary">{message.body}</p>{message.delivery_status === 'SENT' && <div className="mt-2 flex gap-2"><button className="text-xs text-brand-800" onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/mock-response?status_value=READ&response=${encodeURIComponent('Synthetic student read event')}`, {}, token || undefined))}>Record synthetic read</button><button className="text-xs text-brand-800" onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/mock-response?status_value=REPLIED&response=${encodeURIComponent('Synthetic student replied and would like to discuss support')}`, {}, token || undefined))}>Record synthetic reply</button></div>}</div>)}</div></section>

      <section className="neo-card p-5"><h2 className="font-semibold">Meetings</h2><div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3"><label className="text-sm">Date and time<input className="neo-input mt-1" type="datetime-local" value={meetingAt} onChange={(event) => setMeetingAt(event.target.value)} /></label><label className="text-sm">Purpose<input className="neo-input mt-1" value={meetingPurpose} onChange={(event) => setMeetingPurpose(event.target.value)} /></label><div className="flex items-end"><NeoButton loading={busy} onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/meetings`, { meeting_at: new Date(meetingAt).toISOString(), purpose: meetingPurpose }, token || undefined))}><Clock3 size={15} className="mr-1.5 inline" />Schedule meeting</NeoButton></div></div><div className="mt-3 space-y-2">{(data.meetings || []).map((meeting) => <div key={meeting.meeting_id} className="flex flex-wrap items-center justify-between gap-2 border-t border-ns-divider pt-3 text-sm"><span>{new Date(meeting.meeting_at).toLocaleString()} · {meeting.purpose}</span><select className="neo-input w-auto py-1" defaultValue={meeting.status} onChange={(event) => void action(() => api.patch(`/workflow/advisor/meetings/${meeting.meeting_id}`, { status: event.target.value }, token || undefined))}>{['MEETING_SCHEDULED', 'MEETING_COMPLETED', 'STUDENT_DID_NOT_ATTEND', 'MEETING_CANCELLED'].map((status) => <option key={status}>{status}</option>)}</select></div>)}</div></section>

      <section className="neo-card p-5"><h2 className="flex items-center gap-2 font-semibold"><Shield size={16} />Advisor-only notes</h2><p className="mt-1 text-xs text-ns-text-muted">Not visible to lecturers or students.</p><textarea className="neo-input mt-3" rows={3} value={privateNote} onChange={(event) => setPrivateNote(event.target.value)} placeholder="Record a confidential case note…" /><NeoButton className="mt-2" loading={busy} onClick={() => void action(() => api.post(`/workflow/advisor/referrals/${referralId}/notes`, { note: privateNote }, token || undefined))}>Save private note</NeoButton><div className="mt-4 space-y-2">{(data.advisor_notes || []).map((note) => <div key={note.note_id} className="border-t border-ns-divider pt-2"><p className="text-sm whitespace-pre-wrap">{note.note}</p><p className="text-xs text-ns-text-muted">{new Date(note.created_at).toLocaleString()}</p></div>)}</div></section>

      {data.comparison ? (
        <section className="space-y-3">
          <ProgressComparisonCard comparison={data.comparison} title="Progress since referral" />
          <div className="neo-card flex flex-wrap items-center justify-between gap-3 p-4" role="status">
            <div><p className="text-xs font-semibold uppercase tracking-wide text-ns-text-muted">Outcome signal</p><p className="mt-1 text-sm font-semibold text-ns-text-primary">{data.comparison.summary}</p></div>
            <span className={`neo-chip ${data.comparison.direction === 'IMPROVED' ? 'bg-emerald-50 text-ns-success' : data.comparison.direction === 'DECLINED' ? 'bg-red-50 text-ns-danger' : 'bg-amber-50 text-ns-warning'}`}>{data.comparison.direction}</span>
          </div>
        </section>
      ) : (
        <section className="neo-card p-5"><h2 className="font-semibold">Progress since referral</h2><p className="mt-2 text-sm text-ns-text-muted">No academic baseline is recorded for this referral yet. A baseline is captured automatically when a lecturer refers the student, which enables before-and-after follow-up comparison.</p></section>
      )}

      <section className="neo-card p-5"><h2 className="font-semibold">Intervention timeline</h2><ol className="mt-4 space-y-3">{data.timeline.map((event, index) => <li key={`${event.occurred_at}-${index}`} className="border-l-2 border-brand-300 pl-4"><p className="text-xs text-ns-text-muted">{new Date(event.occurred_at).toLocaleString()}</p><p className="text-sm">{event.summary}</p></li>)}</ol></section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3"><p className="text-xs text-ns-text-muted">{label}</p><p className="mt-1 font-semibold text-brand-800">{value}</p></div>;
}
