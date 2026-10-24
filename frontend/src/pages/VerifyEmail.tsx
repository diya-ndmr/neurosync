import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, MailCheck } from 'lucide-react';
import NeoButton from '../components/Buttons/NeoButton';
import { api } from '../services/api';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [complete, setComplete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleVerify = async () => {
    setLoading(true);
    setError('');
    try {
      await api.post('/auth/verify-email', { token });
      setComplete(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not confirm this email address.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ai-gradient flex items-center justify-center p-6">
      <div className="neo-card w-full max-w-md p-8 text-center md:p-10">
        <div className="neo-card mx-auto mb-5 flex h-16 w-16 items-center justify-center">
          {complete
            ? <CheckCircle2 size={32} className="text-emerald-600" />
            : <MailCheck size={32} className="text-brand-600" />}
        </div>
        <h1 className="text-2xl font-extrabold text-ink">
          {complete ? 'Email confirmed' : 'Confirm your email'}
        </h1>
        <p className="mt-2 text-sm text-ink-faint">
          {complete
            ? 'Your account is ready. Sign in to continue.'
            : 'Confirm the email address used for your NeuroSync account.'}
        </p>
        {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
        <div className="mt-6">
          {complete ? (
            <Link to="/login" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
              Continue to sign in
            </Link>
          ) : !token ? (
            <p role="alert" className="text-sm text-red-600">This confirmation link is missing its token.</p>
          ) : (
            <NeoButton type="button" size="lg" className="w-full" loading={loading} onClick={handleVerify}>
              Confirm email address
            </NeoButton>
          )}
        </div>
      </div>
    </div>
  );
}
