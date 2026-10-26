import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import NeoButton from '../components/Buttons/NeoButton';
import Logo from '../components/Logo';
import { requireSupabase, supabaseErrorMessage } from '../services/supabase';

export default function ResetPassword() {
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    try {
      requireSupabase().auth.getSession()
        .then(({ data, error: sessionError }) => {
          if (!active) return;
          if (sessionError) setError(supabaseErrorMessage(sessionError));
          else if (!data.session) setError('This password reset link is invalid or has expired. Request a new one.');
          else setReady(true);
        })
        .catch((reason: unknown) => {
          if (active) setError(supabaseErrorMessage(reason));
        });
    } catch (reason) {
      setError(supabaseErrorMessage(reason));
    }
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const client = requireSupabase();
      const { error: updateError } = await client.auth.updateUser({ password });
      if (updateError) throw updateError;
      const { error: signOutError } = await client.auth.signOut();
      if (signOutError) throw signOutError;
      navigate('/login', { replace: true, state: { passwordReset: true } });
    } catch (reason) {
      setError(supabaseErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-stage min-h-screen flex items-center justify-center p-6">
      <div className="login-form-panel neo-card w-full max-w-md p-8 md:p-10">
        <Logo size="md" className="mb-6" />
        <h1 className="text-2xl font-extrabold text-ink">Choose a new password</h1>
        {ready ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm font-semibold text-ink">
              New password
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="neo-input mt-1.5"
              />
            </label>
            <label className="block text-sm font-semibold text-ink">
              Confirm new password
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="neo-input mt-1.5"
              />
            </label>
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <NeoButton type="submit" size="lg" className="w-full" loading={loading}>
              Update password
            </NeoButton>
          </form>
        ) : (
          <div className="mt-6 space-y-4">
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <Link to="/forgot-password" className="text-sm font-semibold text-brand-600">
              Request another reset link
            </Link>
          </div>
        )}
        <Link to="/login" className="mt-6 block text-center text-sm font-semibold text-brand-600">
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
