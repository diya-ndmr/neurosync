import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Bell, Moon, Palette, LayoutDashboard } from 'lucide-react';
import { usePersonalization, type Personalization } from '../../context/PersonalizationContext';
import { useToast } from '../../components/Toast';

export default function SettingsPage() {
  const { showToast } = useToast();
  const { preferences, loading, error, savePreferences } = usePersonalization();
  const [draft, setDraft] = useState<Personalization>(preferences);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => setDraft(preferences), [preferences]);

  const update = <K extends keyof Personalization>(key: K, value: Personalization[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      await savePreferences(draft);
      showToast('Your preferences were saved to your account.');
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Preferences could not be saved.';
      setSaveError(message);
      showToast(message, 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="neo-card p-6 text-sm text-ink-soft">Loading saved preferences…</div>;

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
            <Settings size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-ink">Settings</h1>
            <p className="text-sm text-ink-soft">Personalise your NeuroSync experience across devices</p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="neo-card p-6"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <Palette size={20} />
            </div>
            <h3 className="font-bold text-ink">Appearance</h3>
          </div>
          <div className="space-y-4">
            <label className="block text-sm font-medium">Theme<select className="neo-input mt-1" value={draft.theme} onChange={(event) => update('theme', event.target.value as Personalization['theme'])}><option value="light">Light</option><option value="dark">Dark</option><option value="system">Match device settings</option></select></label>
            <label className="block text-sm font-medium">Accent colour<select className="neo-input mt-1" value={draft.accent} onChange={(event) => update('accent', event.target.value as Personalization['accent'])}><option value="blue">Blue</option><option value="purple">Purple</option><option value="green">Green</option><option value="neutral">Neutral</option></select></label>
            <label className="block text-sm font-medium">Text size<select className="neo-input mt-1" value={draft.text_size} onChange={(event) => update('text_size', event.target.value as Personalization['text_size'])}><option value="default">Default</option><option value="large">Large</option></select></label>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="neo-card p-6">
          <div className="flex items-center gap-3 mb-5"><div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800"><LayoutDashboard size={20} /></div><div><h3 className="font-bold text-ink">Dashboard & reminders</h3><p className="text-xs text-ink-faint">Preferences are saved to your account. Reminder delivery requires an institution notification service.</p></div></div>
          <div className="space-y-4">
            <label className="block text-sm font-medium">Dashboard spacing<select className="neo-input mt-1" value={draft.layout} onChange={(event) => update('layout', event.target.value as Personalization['layout'])}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label>
            <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={draft.study_reminders} onChange={(event) => update('study_reminders', event.target.checked)} />Enable study and task reminders</label>
            <label className="block text-sm font-medium">Reminder frequency<select className="neo-input mt-1" disabled={!draft.study_reminders} value={draft.reminder_frequency} onChange={(event) => update('reminder_frequency', event.target.value as Personalization['reminder_frequency'])}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="off">Off</option></select></label>
            <label className="block text-sm font-medium">Preferred study start time<input className="neo-input mt-1" type="time" value={draft.preferred_study_start} onChange={(event) => update('preferred_study_start', event.target.value)} /></label>
            <label className="block text-sm font-medium">Time zone<input className="neo-input mt-1" value={draft.timezone} onChange={(event) => update('timezone', event.target.value)} placeholder="Africa/Johannesburg" /></label>
            <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={draft.weekly_summary} onChange={(event) => update('weekly_summary', event.target.checked)} />Receive a weekly academic progress summary</label>
          </div>
        </motion.div>
      </div>

      <div className="neo-card p-5">
        <div className="flex items-center gap-2 font-semibold"><Moon size={17} /> Preview settings</div>
        <p className="mt-2 text-sm text-ink-soft">Theme: {draft.theme} · Accent: {draft.accent} · Layout: {draft.layout} · Study time: {draft.preferred_study_start} ({draft.timezone}) · Study reminders: {draft.study_reminders ? 'On' : 'Off'} · Weekly summary: {draft.weekly_summary ? 'On' : 'Off'}</p>
      </div>
      {(error || saveError) && <p role="alert" className="text-sm text-ns-danger">{saveError || error}</p>}
      <div className="flex justify-end">
        <button type="button" onClick={() => void handleSave()} disabled={saving} className="neo-btn inline-flex items-center gap-2 px-5 py-3 text-sm"><Bell size={16} />{saving ? 'Saving…' : 'Save preferences'}</button>
      </div>
    </div>
  );
}
