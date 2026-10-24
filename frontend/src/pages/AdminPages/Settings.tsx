import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Database, Bell, Shield, BrainCircuit } from 'lucide-react';
import NeoButton from '../../components/Buttons/NeoButton';
import { useToast } from '../../components/Toast';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';

interface MoodleStatus {
  configured: boolean;
  base_url: string | null;
  connection_status: 'not_configured' | 'ready_to_test';
}

interface MoodleConnectionResult {
  connected: boolean;
  connection_status: 'connected';
  site_name: string;
  release: string | null;
}

export default function SettingsPage() {
  const { showToast } = useToast();
  const { token } = useAuth();
  const [saved, setSaved] = useState(false);
  const [moodleStatus, setMoodleStatus] = useState<MoodleStatus | null>(null);
  const [moodleResult, setMoodleResult] = useState<MoodleConnectionResult | null>(null);
  const [moodleLoading, setMoodleLoading] = useState(true);
  const [moodleTesting, setMoodleTesting] = useState(false);
  const [moodleError, setMoodleError] = useState<string | null>(null);
  const [form, setForm] = useState({
    systemName: 'NeuroSync',
    aiModel: 'Gradient Boost v1.0',
    riskThreshold: '70',
    retentionDays: '90',
    emailNotifications: true,
    smsNotifications: false,
    autoPredictions: true,
    twoFactor: false
  });

  useEffect(() => {
    let active = true;
    api
      .get<MoodleStatus>('/moodle/status', token ?? undefined)
      .then((status) => {
        if (active) setMoodleStatus(status);
      })
      .catch(() => {
        if (active) setMoodleError('Unable to load Moodle connection settings.');
      })
      .finally(() => {
        if (active) setMoodleLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  const testMoodleConnection = async () => {
    setMoodleTesting(true);
    setMoodleError(null);
    setMoodleResult(null);
    try {
      const result = await api.post<MoodleConnectionResult>('/moodle/test', {}, token ?? undefined);
      setMoodleResult(result);
      showToast('Moodle connection verified.', 'success');
    } catch (error) {
      setMoodleError(error instanceof Error ? error.message : 'Moodle connection test failed.');
    } finally {
      setMoodleTesting(false);
    }
  };

  const handleSave = () => {
    setSaved(true);
    showToast('Settings saved for this demo session.', 'info');
    setTimeout(() => setSaved(false), 1500);
  };

  const toggle = (key: keyof typeof form) => {
    setForm((prev) => ({ ...prev, [key]: !prev[key] }));
    showToast('Preference changed for this demo session.', 'info');
  };

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
            <h1 className="text-2xl font-extrabold text-ink">System Configuration</h1>
            <p className="text-sm text-ink-soft">Manage NeuroSync platform settings</p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="neo-card p-6"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <Settings size={20} />
            </div>
            <h3 className="font-bold text-ink">General</h3>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-ink mb-1.5">System name</label>
              <input
                value={form.systemName}
                onChange={(e) => setForm({ ...form, systemName: e.target.value })}
                className="neo-input"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-ink mb-1.5">Active AI model</label>
              <select
                value={form.aiModel}
                onChange={(e) => setForm({ ...form, aiModel: e.target.value })}
                className="neo-input"
              >
                <option>Gradient Boost v1.0</option>
                <option>Random Forest v1.0</option>
                <option>Logistic Regression v1.0</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-semibold text-ink mb-1.5">High-risk threshold (%)</label>
                <input
                  type="number"
                  value={form.riskThreshold}
                  onChange={(e) => setForm({ ...form, riskThreshold: e.target.value })}
                  className="neo-input"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-ink mb-1.5">Data retention (days)</label>
                <input
                  type="number"
                  value={form.retentionDays}
                  onChange={(e) => setForm({ ...form, retentionDays: e.target.value })}
                  className="neo-input"
                />
              </div>
            </div>
          </div>
        </motion.div>

        {/* AI & ML */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="neo-card p-6"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <BrainCircuit size={20} />
            </div>
            <h3 className="font-bold text-ink">AI & Machine Learning</h3>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">Automatic predictions</p>
                <p className="text-xs text-ink-faint">Run daily risk predictions</p>
              </div>
              <button
                onClick={() => toggle('autoPredictions')}
                className={`w-12 h-6 rounded-full transition-colors relative ${
                  form.autoPredictions ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                    form.autoPredictions ? 'translate-x-6.5' : 'translate-x-0.5'
                  }`}
                  style={{ left: form.autoPredictions ? 'auto' : '2px', right: form.autoPredictions ? '2px' : 'auto' }}
                />
              </button>
            </div>
            <div className="rounded-2xl bg-mint-50/70 p-4">
              <p className="text-sm font-bold text-ink">Model performance</p>
              <p className="text-xs text-ink-faint mt-1">
                Gradient Boost v1.0 — Accuracy: 87.3% | Precision: 84.6% | Recall: 82.1%
              </p>
              <div className="mt-2 h-1.5 rounded-full bg-brand-200">
                <div className="h-full w-[87%] rounded-full bg-brand-600" />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Notifications */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="neo-card p-6"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <Bell size={20} />
            </div>
            <h3 className="font-bold text-ink">Notifications</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">Email notifications</p>
                <p className="text-xs text-ink-faint">Receive alerts via email</p>
              </div>
              <button
                onClick={() => toggle('emailNotifications')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.emailNotifications ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.emailNotifications ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">SMS notifications</p>
                <p className="text-xs text-ink-faint">Receive alerts via SMS</p>
              </div>
              <button
                onClick={() => toggle('smsNotifications')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.smsNotifications ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.smsNotifications ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
          </div>
        </motion.div>

        {/* Security */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="neo-card p-6"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <Shield size={20} />
            </div>
            <h3 className="font-bold text-ink">Security</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">Two-factor authentication</p>
                <p className="text-xs text-ink-faint">Extra layer of security</p>
              </div>
              <button
                onClick={() => toggle('twoFactor')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.twoFactor ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.twoFactor ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
            <div className="rounded-2xl bg-mint-50/70 p-4">
              <p className="text-sm font-bold text-ink">Data encryption</p>
              <p className="text-xs text-ink-faint mt-1">
                All data encrypted at rest (AES-256) and in transit (TLS 1.3).
              </p>
              <div className="mt-2 flex items-center gap-2 text-xs text-emerald-600 font-semibold">
                <Shield size={14} />
                Active
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-6"
        aria-labelledby="moodle-integration-heading"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 shrink-0 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
              <Database size={20} />
            </div>
            <div>
              <h2 id="moodle-integration-heading" className="font-bold text-ink">Moodle integration</h2>
              <p className="mt-1 text-sm text-ink-soft">
                {moodleLoading
                  ? 'Checking backend configuration…'
                  : moodleResult
                    ? `Connected to ${moodleResult.site_name}${moodleResult.release ? ` (${moodleResult.release})` : ''}.`
                    : moodleStatus?.configured
                      ? 'Configured on the backend; connection has not been tested in this session.'
                      : 'Not configured. Add the Moodle URL and token to the backend environment.'}
              </p>
              {moodleStatus?.base_url && (
                <p className="mt-1 text-xs text-ink-faint">Moodle URL: {moodleStatus.base_url}</p>
              )}
              {moodleError && (
                <p role="alert" className="mt-2 text-sm text-red-700">{moodleError}</p>
              )}
            </div>
          </div>
          <NeoButton
            variant="secondary"
            size="sm"
            loading={moodleTesting}
            disabled={moodleLoading || !moodleStatus?.configured}
            onClick={testMoodleConnection}
          >
            Test connection
          </NeoButton>
        </div>
      </motion.section>

      {/* Save */}
      <div className="flex justify-end">
        <NeoButton onClick={handleSave} loading={saved}>
          {saved ? 'Settings Saved!' : 'Save Settings'}
        </NeoButton>
      </div>
    </div>
  );
}
