import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, ArrowRight, Building2, GraduationCap } from 'lucide-react';
import Logo from '../../components/Logo';
import NeoButton from '../../components/Buttons/NeoButton';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';

type MicrosoftSignInComponent = typeof import('../../components/MicrosoftSignIn').default;

interface DemoProfile {
  label: string;
  email: string;
  password: string;
}

export default function Login() {
  const { login, loginWithMicrosoft } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [portal, setPortal] = useState<'student' | 'staff'>('student');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoProfiles, setDemoProfiles] = useState<DemoProfile[]>([]);
  const [MicrosoftSignIn, setMicrosoftSignIn] = useState<MicrosoftSignInComponent | null>(null);
  const showDemo = import.meta.env.DEV && demoProfiles.length > 0 && MicrosoftSignIn !== null;

  const sessionExpired = (location.state as { reason?: string } | null)?.reason === 'session-expired';
  const passwordReset = (location.state as { passwordReset?: boolean } | null)?.passwordReset === true;

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    let active = true;
    Promise.all([
      import('../../dev/demoProfiles'),
      import('../../components/MicrosoftSignIn')
    ]).then(([{ default: profiles }, { default: signInComponent }]) => {
      if (active) {
        setDemoProfiles(profiles);
        setMicrosoftSignIn(() => signInComponent);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const roleRoute: Record<string, string> = {
    student: '/student/dashboard',
    lecturer: '/lecturer/dashboard',
    advisor: '/advisor/dashboard',
    admin: '/admin/dashboard'
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      // Persist remember preference
      if (!remember) {
        localStorage.setItem('neurosync_session', 'session');
      } else {
        localStorage.removeItem('neurosync_session');
      }
      navigate(roleRoute[user.role]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMicrosoft = async (ssoEmail: string) => {
    setError('');
    try {
      const user = await loginWithMicrosoft(ssoEmail);
      navigate(roleRoute[user.role]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Microsoft sign-in failed');
    }
  };

  const fillDemo = (demo: DemoProfile) => {
    setEmail(demo.email);
    setPassword(demo.password);
    setError('');
  };

  return (
    <div className="login-stage min-h-screen text-ns-text-primary flex items-center justify-center p-4 sm:p-6">

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="login-shell w-full max-w-[1120px] grid md:grid-cols-[0.95fr_1.05fr] gap-0 neo-card overflow-hidden"
      >
        {/* Left side: Hero/Info */}
        <div className="login-hero hidden md:flex flex-col justify-between p-8 lg:p-12 xl:p-14">
          <div className="relative z-10">
            <Logo size="lg" inverse />
          </div>
          <div className="relative z-10 max-w-lg space-y-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">Student-first support</p>
            <h1 className="text-4xl xl:text-[3.25rem] font-bold leading-[1.12] text-white tracking-tight">
              Intelligent campus
              <br />
              <span className="text-emerald-200">wellbeing platform</span>
            </h1>
            <p className="max-w-md text-white/75 text-lg leading-relaxed">
              Proactive care, clearer insights, and personalized guidance to help every student move forward.
            </p>
            <div className="grid grid-cols-3 gap-3 pt-3">
              {[
                ['01', 'Academic progress'],
                ['02', 'Attendance'],
                ['03', 'Student support']
              ].map(([number, label]) => (
                <div key={number} className="border-t border-white/25 pt-3">
                  <p className="text-xs font-semibold text-emerald-200">{number}</p>
                  <p className="mt-1 text-xs font-medium text-white/75">{label}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="relative z-10 flex items-center gap-3 text-xs font-medium text-white/60">
            <span className="h-2 w-2 rounded-full bg-emerald-300" />
            <span>Built to support the whole student journey</span>
          </div>
        </div>

        {/* Right side: Form */}
        <div className="login-form-panel p-7 sm:p-8 md:p-12 xl:p-14 flex flex-col justify-center">
          <div className="flex flex-col items-center md:items-start mb-8">
            <div className="md:hidden mb-6">
              <Logo size="md" />
            </div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-brand-700">NeuroSync portal</p>
            <h2 className="text-3xl font-bold tracking-tight text-ns-text-primary">Welcome back</h2>
            <p className="text-ns-text-muted font-medium text-sm mt-2">Choose your portal to continue.</p>
          </div>

          <div className="mb-7 grid grid-cols-2 gap-3" aria-label="Choose your portal">
            <button
              type="button"
              aria-pressed={portal === 'student'}
              onClick={() => setPortal('student')}
              className={`portal-choice flex min-h-[76px] items-center gap-3 rounded-xl border p-3 text-left transition-colors ${portal === 'student' ? 'portal-choice-active' : 'border-ns-border bg-ns-surface hover:bg-ns-surface-secondary'}`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-800"><GraduationCap size={20} /></span>
              <span><span className="block text-sm font-semibold text-ns-text-primary">Student</span><span className="mt-0.5 block text-xs text-ns-text-muted">My learning</span></span>
            </button>
            <button
              type="button"
              aria-pressed={portal === 'staff'}
              onClick={() => setPortal('staff')}
              className={`portal-choice flex min-h-[76px] items-center gap-3 rounded-xl border p-3 text-left transition-colors ${portal === 'staff' ? 'portal-choice-active' : 'border-ns-border bg-ns-surface hover:bg-ns-surface-secondary'}`}
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-800"><Building2 size={20} /></span>
              <span><span className="block text-sm font-semibold text-ns-text-primary">University staff</span><span className="mt-0.5 block text-xs text-ns-text-muted">Lecturer · Advisor · Admin</span></span>
            </button>
          </div>

          <p className="mb-5 text-sm font-medium text-ns-text-secondary">
            {portal === 'student' ? 'Sign in to your student workspace.' : 'Sign in to your university staff workspace.'}
          </p>
          <p className="-mt-4 mb-5 text-xs text-ns-text-muted">Your account role determines which workspace opens after sign-in.</p>

          {error && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-ns-danger font-semibold"
            >
              {error}
            </motion.div>
          )}

          {sessionExpired && !error && (
            <div role="status" className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 font-semibold">
              Your session expired. Please sign in again to continue.
            </div>
          )}
          {passwordReset && (
            <div role="status" className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 font-semibold">
              Your password was updated. Sign in with your new password.
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-ns-text-secondary mb-2">Email address</label>
              <div className="relative group">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ns-text-muted group-focus-within:text-brand-800 transition-colors" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@university.edu"
                  className="neo-input pl-12"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-ns-text-secondary mb-2">Password</label>
              <div className="relative group">
                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ns-text-muted group-focus-within:text-brand-800 transition-colors" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="neo-input pl-12 pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-ns-text-muted hover:text-brand-800 transition-colors"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-ns-text-secondary cursor-pointer hover:text-ns-text-primary transition-colors">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 rounded border-ns-border accent-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500"
                />
                Remember Session
              </label>
              <Link to="/forgot-password" title="Password recovery" className="text-sm font-semibold text-brand-800 hover:underline underline-offset-4">
                Forgot password?
              </Link>
            </div>

            <NeoButton type="submit" loading={loading} className="w-full group mt-4 h-12">
              <span className="flex items-center justify-center gap-2">
                Sign in
                {!loading && <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />}
              </span>
            </NeoButton>
          </form>

          {MicrosoftSignIn && <MicrosoftSignIn onSelect={handleMicrosoft} error={error} />}

          {showDemo && <div className="mt-12">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-px flex-1 bg-ns-divider" />
              <span className="text-xs font-semibold uppercase tracking-wider text-ns-text-muted">Demo profiles</span>
              <div className="h-px flex-1 bg-ns-divider" />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {demoProfiles.map((d) => (
                <button
                  key={d.label}
                  type="button"
                  onClick={() => fillDemo(d)}
                  className="p-3 bg-white border border-ns-border rounded-lg hover:bg-brand-50 hover:border-brand-200 transition-colors text-center"
                >
                  <p className="text-xs font-semibold text-brand-800">{d.label}</p>
                  <p className="mt-1 break-all text-[10px] text-ns-text-muted">{d.email}</p>
                </button>
              ))}
            </div>
            <p className="mt-3 text-center text-xs text-ns-text-muted">Password: <code>demo1234</code> · Development demo only</p>
          </div>}
        </div>
      </motion.div>
    </div>
  );
}
