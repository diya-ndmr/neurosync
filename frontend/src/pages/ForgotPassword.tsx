import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import NeoButton from '../components/Buttons/NeoButton';
import { sendPasswordResetEmail } from 'firebase/auth';
import { firebaseErrorMessage, requireFirebaseAuth } from '../services/firebase';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await sendPasswordResetEmail(requireFirebaseAuth(), email);
      setSent(true);
    } catch (reason) {
      setError(firebaseErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ai-gradient flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        <div className="neo-card p-8 md:p-10">
          <div className="flex flex-col items-center mb-8">
            <div className="neo-card p-4 mb-5">
              <img
                src="/src/assets/neurosync-logo/neurosync-logo.jpg"
                alt="NeuroSync logo"
                className="w-20 h-20 rounded-3xl object-cover"
              />
            </div>
            <h2 className="text-2xl font-extrabold text-ink tracking-tight">
              {sent ? 'Check your email' : 'Reset password'}
            </h2>
            <p className="text-sm text-ink-faint mt-1 text-center">
              {sent
                ? 'We sent a reset link to your email address.'
                : 'Enter your email and we will send you a reset link.'}
            </p>
          </div>

          {sent ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center gap-4"
            >
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 size={32} className="text-emerald-600" />
              </div>
              <p className="text-sm text-ink-soft text-center">
                We've sent a password reset link to <strong className="text-ink">{email}</strong>.
                Follow Firebase's instructions to choose a new password.
              </p>
              <Link to="/login" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
                Back to login
              </Link>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-ink mb-1.5">Email</label>
                <div className="relative">
                  <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@university.edu"
                    className="neo-input pl-11"
                  />
                </div>
              </div>

              {error && <p role="alert" className="text-sm text-red-600">{error}</p>}

              <NeoButton type="submit" size="lg" className="w-full" loading={loading}>
                Send Reset Link
              </NeoButton>
            </form>
          )}

          <Link
            to="/login"
            className="mt-6 flex items-center justify-center gap-2 text-sm font-semibold text-brand-600 hover:text-brand-700"
          >
            <ArrowLeft size={16} />
            Back to login
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
