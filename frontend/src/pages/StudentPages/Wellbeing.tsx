import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { HeartPulse, SmilePlus } from 'lucide-react';
import WellbeingCard from '../../components/Cards/WellbeingCard';
import NeoButton from '../../components/Buttons/NeoButton';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useApiData } from '../../hooks/useApiData';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import { fetchMyStudentProfile, fetchWellbeingHistory } from '../../services/liveData';
import { formatDate } from '../../utils/helpers';
import { useToast } from '../../components/Toast';
import { studentDemoWellbeing, createStudentDemoProfile } from '../../services/studentDemoData';

const wellbeingFallback = { data: studentDemoWellbeing, useWhenEmpty: (rows: typeof studentDemoWellbeing) => rows.length === 0 };

export default function Wellbeing() {
  const { token, user } = useAuth();
  const { showToast } = useToast();
  const profileFallback = useMemo(() => ({ data: createStudentDemoProfile(user) }), [user]);
  const { data: profile, source: profileSource } = useApiData(fetchMyStudentProfile, [], true, profileFallback);
  const { data: history, loading, error, refresh, source: historySource } = useApiData(fetchWellbeingHistory, [], true, wellbeingFallback);
  const [modal, setModal] = useState(false);
  const [mood, setMood] = useState(7);
  const [stress, setStress] = useState(5);
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const demoMode = profileSource === 'offline-demo' || historySource === 'offline-demo' || historySource === 'demo-sample';
  const dataSource = profileSource === 'offline-demo' || historySource === 'offline-demo'
    ? 'offline-demo'
    : demoMode ? 'demo-sample' : 'live';

  const submit = async () => {
    if (demoMode) return;
    if (!token || !profile) {
      setSaveError('Your student profile could not be resolved.');
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await api.post('/wellbeing/checkin', {
        student_id: profile.id,
        mood_score: mood,
        stress_level: stress,
        notes: notes || null
      }, token);
      setModal(false);
      setNotes('');
      refresh();
      showToast('Your wellbeing check-in was saved.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Check-in could not be saved';
      setSaveError(message);
      showToast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState label="Loading your wellbeing record…" />;

  const rows = history ?? [];
  const latest = rows[0];

  return (
    <div className="space-y-6">
      <DataSourceNotice source={dataSource} />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <HeartPulse size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-ink">Wellbeing</h1>
              <p className="text-sm text-ink-soft">Track your mood and stress</p>
            </div>
          </div>
          <NeoButton disabled={demoMode} onClick={() => setModal(true)}>
            <SmilePlus size={17} className="inline mr-1.5" />
            New Check-in
          </NeoButton>
        </div>
      </motion.div>

      {error && <p className="text-sm text-ns-warning">{error}</p>}
      {demoMode && <p role="status" className="text-xs text-ink-faint">Check-ins are read-only in demo mode.</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WellbeingCard
          moodScore={latest?.mood_score ?? null}
          stressLevel={latest?.stress_level ?? null}
          lastCheckin={latest?.created_at ?? ''}
          onCheckin={() => { if (!demoMode) setModal(true); }}
        />
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="neo-card p-6"
        >
          <h3 className="font-bold text-ink mb-4">Mood History</h3>
          <div className="space-y-3">
            {rows.length === 0 && <p className="text-sm text-ink-faint">No check-ins recorded yet.</p>}
            {rows.map((h, i) => (
              <motion.div
                key={h.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.05 * i }}
                className="flex items-center justify-between rounded-2xl bg-white/60 border border-brand-100/60 p-3.5"
              >
                <div>
                  <p className="text-sm font-bold text-ink">{formatDate(h.created_at)}</p>
                  <p className="text-xs text-ink-faint">{h.notes || 'Daily mood check-in'}</p>
                </div>
                <div className="flex gap-3 text-right">
                  <div>
                    <p className="text-lg font-extrabold text-amber-500">{h.mood_score}/10</p>
                    <p className="text-[10px] text-ink-faint">Mood</p>
                  </div>
                  <div>
                    <p className="text-lg font-extrabold text-rose-500">{h.stress_level}/10</p>
                    <p className="text-[10px] text-ink-faint">Stress</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Check-in modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            onClick={() => setModal(false)}
            className="absolute inset-0 bg-ink/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="relative neo-card p-7 w-full max-w-md"
          >
            <h3 className="text-xl font-extrabold text-ink mb-5">Wellbeing Check-in</h3>

            <div className="mb-5">
              <label className="block text-sm font-semibold text-ink mb-2">How is your mood today? ({mood}/10)</label>
              <input
                type="range"
                min="1"
                max="10"
                value={mood}
                onChange={(e) => setMood(Number(e.target.value))}
                className="w-full accent-brand-500"
              />
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>Low</span>
                <span>Great</span>
              </div>
            </div>

            <div className="mb-5">
              <label className="block text-sm font-semibold text-ink mb-2">Stress level? ({stress}/10)</label>
              <input
                type="range"
                min="1"
                max="10"
                value={stress}
                onChange={(e) => setStress(Number(e.target.value))}
                className="w-full accent-rose-500"
              />
              <div className="flex justify-between text-xs text-ink-faint mt-1">
                <span>Relaxed</span>
                <span>Overwhelmed</span>
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold text-ink mb-2">Notes (optional)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="How are you feeling?"
                className="neo-input resize-none"
              />
            </div>

            <div className="flex gap-3">
              <NeoButton variant="secondary" className="flex-1" onClick={() => setModal(false)}>
                Cancel
              </NeoButton>
              <NeoButton className="flex-1" onClick={() => void submit()} loading={saving}>
                {saving ? 'Saving…' : 'Save Check-in'}
              </NeoButton>
            </div>
            {saveError && <p className="mt-3 text-xs text-ns-danger">{saveError}</p>}
          </motion.div>
        </div>
      )}
    </div>
  );
}
