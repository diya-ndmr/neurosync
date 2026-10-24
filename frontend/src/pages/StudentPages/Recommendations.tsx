import { motion } from 'framer-motion';
import { LifeBuoy, Send, Target } from 'lucide-react';
import { useState } from 'react';
import RecommendationCard from '../../components/Cards/RecommendationCard';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useDashboardData } from '../../hooks/useDashboardData';
import type { StudentDashboardData } from '../../types';
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
