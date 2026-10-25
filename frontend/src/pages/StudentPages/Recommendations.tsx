import { motion } from 'framer-motion';
import { LifeBuoy, Send, Target } from 'lucide-react';
import { useEffect, useState } from 'react';
import RecommendationCard from '../../components/Cards/RecommendationCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useDashboardData } from '../../hooks/useDashboardData';
import type { StudentDashboardData } from '../../types';
import type { LearningSupportItem, WellnessReferral, WellnessSlot } from '../../services/liveData';
import { fetchLearningSupport } from '../../services/liveData';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { useToast } from '../../components/Toast';

export default function Recommendations() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [requestType, setRequestType] = useState('Academic support');
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const { data, loading, source, refresh } = useDashboardData<StudentDashboardData>('student');
  const [completingId, setCompletingId] = useState<string | null>(null);
  const [learningSupport, setLearningSupport] = useState<LearningSupportItem[]>([]);
  const [wellnessReferrals, setWellnessReferrals] = useState<WellnessReferral[]>([]);
  const [wellnessSlots, setWellnessSlots] = useState<WellnessSlot[]>([]);
  const [appointments, setAppointments] = useState<{ id: string; status: string; starts_at: string; location: string }[]>([]);
  const [supportError, setSupportError] = useState<string | null>(null);
  const [bookingId, setBookingId] = useState<string | null>(null);

  const refreshSupport = async () => {
    if (!token) return;
    try {
      const [learning, referrals, booked] = await Promise.all([
        fetchLearningSupport(token),
        api.get<WellnessReferral[]>('/wellbeing/referrals/mine', token),
        api.get<{ id: string; status: string; starts_at: string; location: string }[]>('/wellbeing/appointments', token)
      ]);
      setLearningSupport(learning);
      setWellnessReferrals(referrals);
      setAppointments(booked);
      if (referrals.some((referral) => referral.status === 'active')) {
        setWellnessSlots(await api.get<WellnessSlot[]>('/wellbeing/slots', token));
      } else {
        setWellnessSlots([]);
      }
      setSupportError(null);
    } catch (requestError) {
      setSupportError(requestError instanceof Error ? requestError.message : 'Support recommendations could not be loaded.');
    }
  };

  useEffect(() => { void refreshSupport(); }, [token]);

  const updateResource = async (resourceId: string, status: 'viewed' | 'completed') => {
    if (!token) return;
    try {
      await api.patch(`/learning/resources/${resourceId}/progress`, { status }, token);
      await refreshSupport();
    } catch (requestError) {
      showToast(requestError instanceof Error ? requestError.message : 'Resource progress could not be saved.', 'error');
    }
  };

  const openResource = async (resource: LearningSupportItem['resources'][number]) => {
    if (!token) return;
    try {
      if (resource.resource_type === 'file') {
        const file = await api.getBlob(resource.url, token);
        const link = document.createElement('a');
        link.href = URL.createObjectURL(file);
        link.download = resource.filename || resource.title;
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      } else {
        window.open(resource.url, '_blank', 'noopener,noreferrer');
      }
      await updateResource(resource.id, 'viewed');
    } catch (requestError) {
      showToast(requestError instanceof Error ? requestError.message : 'Resource could not be opened.', 'error');
    }
  };

  const bookWellness = async (referral: WellnessReferral, slot: WellnessSlot) => {
    if (!token) return;
    setBookingId(slot.id);
    try {
      await api.post('/wellbeing/appointments', { referral_id: referral.id, slot_id: slot.id }, token);
      showToast('Your confidential Wellness appointment is confirmed.');
      await refreshSupport();
    } catch (requestError) {
      showToast(requestError instanceof Error ? requestError.message : 'Appointment could not be booked.', 'error');
    } finally {
      setBookingId(null);
    }
  };

  const completeRecommendation = async (recommendationId: string) => {
    if (!token) return;
    setCompletingId(recommendationId);
    try {
      await api.patch(`/predictions/recommendations/${recommendationId}/complete`, {}, token);
      showToast('Suggestion marked complete.');
      refresh();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Could not update suggestion.', 'error');
    } finally {
      setCompletingId(null);
    }
  };

  if (loading) return <LoadingState label="Loading your recommendations…" />;
  if (!data) return null;
  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
            <Target size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-ink">Recommendations</h1>
            <p className="text-sm text-ink-soft">
              Practical suggestions based on your recorded progress
            </p>
          </div>
        </div>
      </motion.div>

      <RecommendationCard recommendations={data.recommendations} onComplete={completeRecommendation} completingId={completingId} />

      <section className="neo-card p-6" aria-labelledby="learning-support-heading">
        <h2 id="learning-support-heading" className="font-bold text-ink">Topic-level learning support</h2>
        <p className="mt-1 text-sm text-ink-soft">Resources are linked to your lecturer's feedback and recorded module data. Marking a resource complete records your activity; it does not claim topic mastery.</p>
        {supportError && <p className="mt-3 text-sm text-ns-danger" role="alert">{supportError}</p>}
        {learningSupport.length === 0 ? <p className="mt-4 text-sm text-ink-faint">No topic-level recommendations have been recorded yet.</p> : (
          <div className="mt-4 space-y-4">
            {learningSupport.map((item) => <article key={item.feedback_id} className="rounded border border-ns-border p-4">
              <h3 className="font-semibold text-ink">{item.module} · {item.topic}</h3>
              <p className="mt-2 text-sm text-ink-soft">{item.feedback}</p>
              <p className="mt-2 text-xs text-ink-faint">{item.recommendation_explanation} {item.performance_context.explanation} {item.performance_context.module_average == null ? '' : `Module assessment average: ${item.performance_context.module_average}%.`}</p>
              <div className="mt-3 flex flex-wrap gap-2">{item.learning_gaps.map((gap) => <span key={gap} className="neo-chip bg-brand-50 text-brand-800">Focus: {gap}</span>)}</div>
              {item.learning_goal && <p className="mt-3 text-sm"><strong>Learning goal:</strong> {item.learning_goal}{item.goal_due_date ? ` · Target date: ${item.goal_due_date}` : ''}</p>}
              <ul className="mt-3 space-y-2">
                {item.resources.map((resource) => <li key={resource.id} className="flex flex-wrap items-center justify-between gap-2 rounded bg-ns-surface-secondary p-3">
                  <div><p className="text-sm font-medium">{resource.title}</p>{resource.description && <p className="text-xs text-ink-soft">{resource.description}</p>}<p className="text-xs text-ink-faint">Source: {resource.provider}{resource.reviewed_by_lecturer ? ' · Lecturer reviewed' : ' · Awaiting lecturer review'} · Progress: {resource.status}</p></div>
                  <div className="flex gap-2"><button type="button" onClick={() => void openResource(resource)} className="neo-btn px-3 py-2 text-xs">{resource.resource_type === 'file' ? 'Download' : 'Open resource'}</button>{resource.status !== 'completed' && <button type="button" onClick={() => void updateResource(resource.id, 'completed')} className="rounded border border-ns-border px-3 py-2 text-xs">Mark complete</button>}</div>
                </li>)}
              </ul>
            </article>)}
          </div>
        )}
      </section>

      <section className="neo-card p-6" aria-labelledby="wellness-recommendation-heading">
        <h2 id="wellness-recommendation-heading" className="font-bold text-ink">Student Wellness Support</h2>
        {wellnessReferrals.some((referral) => referral.status === 'active') ? <>
          <p className="mt-2 text-sm text-ink-soft">Based on a support recommendation from your university, you can book a confidential appointment with Student Wellness.</p>
          <p className="mt-1 text-sm">Your next step: speak with a Student Wellness professional about available support.</p>
          <h3 className="mt-4 text-sm font-semibold">Available appointment slots</h3>
          {wellnessSlots.length === 0 ? <p className="mt-2 text-sm text-ink-faint">No appointment slots are currently available.</p> : wellnessSlots.map((slot) => <div key={slot.id} className="mt-2 flex flex-wrap items-center justify-between gap-3 border border-ns-border p-3">
            <p className="text-sm">{new Date(slot.starts_at).toLocaleString()} · {slot.duration_minutes} min · {slot.location}</p>
            <button type="button" disabled={bookingId === slot.id} onClick={() => void bookWellness(wellnessReferrals.find((referral) => referral.status === 'active')!, slot)} className="neo-btn px-3 py-2 text-xs">{bookingId === slot.id ? 'Booking…' : 'Book a Wellness session'}</button>
          </div>)}
        </> : <p className="mt-2 text-sm text-ink-soft">Wellness booking becomes available when an authorised support professional makes a recommendation; elapsed time alone does not unlock it.</p>}
        {appointments.length > 0 && <div className="mt-4 border-t border-ns-divider pt-4"><h3 className="text-sm font-semibold">Your bookings</h3>{appointments.map((appointment) => <p key={appointment.id} className="mt-2 text-sm">{new Date(appointment.starts_at).toLocaleString()} · {appointment.location} · <span className="capitalize">{appointment.status}</span></p>)}</div>}
      </section>

      <section className="neo-card p-6" aria-labelledby="support-request-heading">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-brand-100 bg-brand-50 text-brand-800"><LifeBuoy size={20} /></div>
          <div><h2 id="support-request-heading" className="font-bold text-ink">Ask for support</h2><p className="mt-1 text-sm text-ink-soft">Send a private request to the student support team.</p></div>
        </div>
        <form className="mt-4 space-y-4" onSubmit={async (event) => { event.preventDefault(); if (!token || !message.trim()) return; setSending(true); try { await api.post('/support-requests', { request_type: requestType, message }, token); setMessage(''); showToast('Your support request was sent.'); } catch (error) { showToast(error instanceof Error ? error.message : 'Could not send support request.', 'error'); } finally { setSending(false); } }}>
          <label className="block text-sm font-medium">What do you need help with?<select className="neo-input mt-1" value={requestType} onChange={(event) => setRequestType(event.target.value)}><option>Academic support</option><option>Attendance support</option><option>Wellbeing support</option><option>Financial or personal support</option><option>Other</option></select></label>
          <label className="block text-sm font-medium">Message<textarea className="neo-input mt-1" rows={4} minLength={5} maxLength={2000} required value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Tell us what would help." /></label>
          <button type="submit" disabled={sending || !message.trim()} className="neo-btn inline-flex items-center gap-2 px-4 py-2.5 text-sm"><Send size={15} />{sending ? 'Sending…' : 'Send support request'}</button>
        </form>
      </section>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="neo-card p-6"
      >
        <h3 className="font-bold text-ink mb-3">How recommendations work</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            {
              step: '01',
              title: 'We use recorded information',
              desc: 'NeuroSync uses the academic, attendance and wellbeing records currently available in the app.'
            },
            {
              step: '02',
              title: 'We flag possible concerns',
              desc: 'Prototype risk logic highlights recorded indicators. It is not a continuously running or institution-validated forecast.'
            },
            {
              step: '03',
              title: 'You choose next steps',
              desc: 'Suggestions can help start a conversation with your support team; people—not the model—make decisions about support.'
            }
          ].map((s, i) => (
            <motion.div
              key={s.step}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.1 }}
              className="rounded-2xl bg-white/60 border border-brand-100/60 p-5"
            >
              <p className="text-3xl font-extrabold text-brand-200">{s.step}</p>
              <h4 className="font-bold text-ink mt-2">{s.title}</h4>
              <p className="text-sm text-ink-soft mt-1 leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
