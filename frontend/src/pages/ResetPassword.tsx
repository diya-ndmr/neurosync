import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, LockKeyhole } from 'lucide-react';
import NeoButton from '../components/Buttons/NeoButton';
import { api } from '../services/api';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/reset-password', { token, new_password: password });
      setComplete(true);
    } catch {
      setError('This reset link is invalid or expired. Request a new one and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ai-gradient flex items-center justify-center p-6">
      <div className="neo-card w-full max-w-md p-8 md:p-10">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="neo-card mb-5 p-4">
            <LockKeyhole size={32} className="text-brand-600" />
          </div>
          <h1 className="text-2xl font-extrabold text-ink tracking-tight">
            {complete ? 'Password updated' : 'Choose a new password'}
          </h1>
          <p className="mt-1 text-sm text-ink-faint">
            {complete ? 'You can now sign in with your new password.' : 'Your reset link is valid for 30 minutes.'}
          </p>
        </div>

        {complete ? (
          <Link to="/login" className="block text-center text-sm font-semibold text-brand-600 hover:text-brand-700">
            Back to login
          </Link>
        ) : !token ? (
          <div className="space-y-4 text-center">
            <p role="alert" className="text-sm text-red-600">This reset link is missing its token.</p>
            <Link to="/forgot-password" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
              Request a new reset link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="new-password" className="mb-1.5 block text-sm font-semibold text-ink">New password</label>
              <input
                id="new-password"
                type="password"
                required
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="neo-input"
              />
            </div>
            <div>
              <label htmlFor="confirm-password" className="mb-1.5 block text-sm font-semibold text-ink">Confirm new password</label>
              <input
                id="confirm-password"
                type="password"
                required
                minLength={8}
                maxLength={128}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="neo-input"
              />
            </div>
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <NeoButton type="submit" size="lg" className="w-full" loading={loading}>
              Update Password
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
    </div>
  );
}
