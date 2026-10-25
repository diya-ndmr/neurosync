import { useEffect, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, ArrowRight } from 'lucide-react';
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
    <div className="min-h-screen bg-ns-background text-ns-text-primary flex items-center justify-center p-4 sm:p-6">

      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-[1000px] grid lg:grid-cols-2 gap-0 neo-card overflow-hidden"
      >
        {/* Left side: Hero/Info */}
        <div className="hidden lg:flex flex-col justify-between p-12 bg-ns-black border-r border-white/10">
          <div>
            <Logo size="lg" inverse />
          </div>
          <div className="space-y-6">
            <h1 className="text-4xl font-bold leading-tight text-white tracking-tight">
              Predict.
              <br />
              <span className="text-brand-300">Explain.</span>
              <br />
              Intervene.
            </h1>
            <p className="text-white/70 text-lg leading-relaxed font-medium">
              NeuroSync brings academic progress, attendance, and support work into one clear place.
            </p>
            <div className="flex gap-4">
              <div className="h-1 w-12 bg-brand-500 rounded-full" />
              <div className="h-1 w-6 bg-brand-700 rounded-full" />
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-semibold uppercase tracking-[0.15em] text-white/55">
            <span>© 2026 NeuroSync</span>
            <span className="w-1.5 h-1.5 bg-brand-500 rounded-full" />
            <span>Neuform v3.0</span>
          </div>
        </div>

        {/* Right side: Form */}
        <div className="p-7 sm:p-8 md:p-14 flex flex-col justify-center bg-white">
          <div className="flex flex-col items-center lg:items-start mb-10">
            <div className="lg:hidden mb-6">
              <Logo size="md" />
            </div>
            <h2 className="text-3xl font-bold text-ns-text-primary">Authentication</h2>
            <p className="text-ns-text-muted font-medium text-sm mt-2">Access your intelligence dashboard</p>
          </div>

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
