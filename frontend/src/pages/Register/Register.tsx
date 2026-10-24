import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, User, ArrowRight, ShieldCheck } from 'lucide-react';
import Logo from '../../components/Logo';
import NeoButton from '../../components/Buttons/NeoButton';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';
import type { Role } from '../../types';

const roleOptions: { value: Role; label: string; desc: string }[] = [
  { value: 'student', label: 'Student', desc: 'Track your academic journey' },
  { value: 'lecturer', label: 'Lecturer', desc: 'Monitor your classes' },
  { value: 'advisor', label: 'Advisor', desc: 'Manage student support' }
];

export default function Register() {
  const { register } = useAuth();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [role, setRole] = useState<Role>('student');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [registrationComplete, setRegistrationComplete] = useState(false);
  const [registrationMessage, setRegistrationMessage] = useState('');

  useEffect(() => {
    api.get<{ roles: string[] }>('/auth/registration-options')
      .then(({ roles: allowedRoles }) => {
        const availableRoles = allowedRoles.filter((value): value is Role =>
          roleOptions.some((option) => option.value === value)
        );
        if (!availableRoles.includes('student')) {
          throw new Error('Student registration is not currently available.');
        }
        setRoles(availableRoles);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Could not load registration options.');
      })
      .finally(() => setLoadingRoles(false));
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (loadingRoles || !roles.includes(role)) {
      setError('Registration options are unavailable. Please reload and try again.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const message = await register({ name, email, password, role });
      setRegistrationMessage(message);
      setRegistrationComplete(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ai-gradient flex flex-col lg:flex-row">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between p-12 w-1/2">
        <Logo size="lg" />
        <div className="space-y-6">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl font-extrabold leading-tight text-ink tracking-tight"
          >
            Join the
            <br />
            <span className="text-brand-600">Intelligent</span>
            <br />
            Campus
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="text-ink-soft max-w-md leading-relaxed"
          >
            Create your NeuroSync account and unlock AI-powered insights into your academic
            journey — with proactive support every step of the way.
          </motion.p>
        </div>
        <p className="text-xs text-ink-faint">© 2025 NeuroSync · University Intelligence Platform</p>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="w-full max-w-md"
        >
          <div className="neo-card p-8 md:p-10">
            <div className="flex flex-col items-center mb-7">
              <div className="neo-card p-4 mb-5">
                <img
                  src="/src/assets/neurosync-logo/neurosync-logo.jpg"
                  alt="NeuroSync logo"
                  className="w-24 h-24 rounded-3xl object-cover"
                />
              </div>
              <h2 className="text-2xl font-extrabold text-ink tracking-tight">Create account</h2>
              <p className="text-sm text-ink-faint mt-1">Get started with NeuroSync</p>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-5 rounded-2xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 font-medium"
              >
                {error}
              </motion.div>
            )}

            {registrationComplete ? (
              <div className="space-y-4 text-center" aria-live="polite">
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-900">
                  {registrationMessage}
                </div>
                <p><Link to="/login" className="text-sm font-semibold text-brand-600 hover:text-brand-700">Back to sign in</Link></p>
              </div>
            ) : <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-ink mb-1.5">Full name</label>
                <div className="relative">
                  <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="First name Surname"
                    className="neo-input pl-11"
                  />
                </div>
              </div>

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

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">Password</label>
                  <div className="relative">
                    <Lock size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="neo-input pl-10 pr-9"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-brand-600"
                      aria-label="Toggle password"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">Confirm</label>
                  <div className="relative">
                    <Lock size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      placeholder="••••••••"
                      className="neo-input pl-10"
                    />
                  </div>
                </div>
              </div>

              {loadingRoles ? (
                <p className="text-sm text-ink-faint" role="status">Loading registration options…</p>
              ) : roles.length > 1 ? (
                <div>
                  <label className="block text-sm font-semibold text-ink mb-1.5">Role</label>
                  <div className="grid grid-cols-3 gap-2">
                    {roleOptions.filter((option) => roles.includes(option.value)).map((r) => (
                      <button
                        key={r.value}
                        type="button"
                        onClick={() => setRole(r.value)}
                        className={`rounded-2xl border px-3 py-2.5 text-left transition-all ${
                          role === r.value
                            ? 'border-brand-400 bg-brand-50 shadow-sm'
                            : 'border-brand-100 bg-white/50 hover:bg-brand-50/50'
                        }`}
                      >
                        <p className="text-xs font-bold text-ink">{r.label}</p>
                        <p className="text-[10px] text-ink-faint leading-tight mt-0.5">{r.desc}</p>
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-ink-faint">Admin accounts are created by an administrator, not through public signup.</p>
                </div>
              ) : (
                <p className="text-sm text-ink-faint">
                  Public registration is limited to student accounts. Lecturer and advisor accounts are provisioned by an administrator.
                </p>
              )}

              <NeoButton type="submit" size="lg" className="w-full" loading={loading || loadingRoles} disabled={loadingRoles || !roles.length}>
                <span className="inline-flex items-center gap-2">
                  Create Account
                  <ArrowRight size={18} />
                </span>
              </NeoButton>
            </form>}

            <p className="mt-6 text-center text-sm text-ink-faint">
              Already have an account?{' '}
              <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
                Sign in
              </Link>
            </p>

            <div className="mt-4 flex items-center justify-center gap-2 text-xs text-ink-faint">
              <ShieldCheck size={14} className="text-emerald-500" />
              Your data is encrypted and protected.
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
