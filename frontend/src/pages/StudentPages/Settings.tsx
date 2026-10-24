import { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Bell, Shield, Moon, Lock } from 'lucide-react';
import NeoButton from '../../components/Buttons/NeoButton';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';

export default function SettingsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    emailNotifications: true,
    smsNotifications: false,
    riskAlerts: true,
    weeklyReport: true,
    darkMode: false,
    twoFactor: false
  });

  const handleSave = () => {
    setSaved(true);
    showToast('Preferences saved for this demo session.', 'info');
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
            <h1 className="text-2xl font-extrabold text-ink">Settings</h1>
            <p className="text-sm text-ink-soft">Manage your account preferences</p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notifications */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
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
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">AI risk alerts</p>
                <p className="text-xs text-ink-faint">Notify when risk level changes</p>
              </div>
              <button
                onClick={() => toggle('riskAlerts')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.riskAlerts ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.riskAlerts ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">Weekly summary report</p>
                <p className="text-xs text-ink-faint">Get a weekly progress summary</p>
              </div>
              <button
                onClick={() => toggle('weeklyReport')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.weeklyReport ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.weeklyReport ? 'translate-x-6' : ''
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
          transition={{ delay: 0.1 }}
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
              <p className="text-sm font-bold text-ink">Change password</p>
              <div className="mt-3 space-y-3">
                <input type="password" placeholder="Current password" className="neo-input" />
                <input type="password" placeholder="New password" className="neo-input" />
              </div>
            </div>
            <div className="flex items-center justify-between rounded-2xl bg-mint-50/70 px-4 py-3">
              <div>
                <p className="text-sm font-bold text-ink">Dark mode</p>
                <p className="text-xs text-ink-faint">Coming soon</p>
              </div>
              <button
                onClick={() => toggle('darkMode')}
                className={`w-12 h-6 rounded-full transition-colors ${
                  form.darkMode ? 'bg-brand-500' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`block w-5 h-5 rounded-full bg-white shadow transition-transform translate-x-0.5 ${
                    form.darkMode ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      <div className="flex justify-end">
        <NeoButton onClick={handleSave} loading={saved}>
          <Lock size={16} className="inline mr-1.5" />
          {saved ? 'Saved!' : 'Save Preferences'}
        </NeoButton>
      </div>
    </div>
  );
}

