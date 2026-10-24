import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

export interface ApiData<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Runs an authenticated request and reports loading/error state.
 *
 * `fetcher` is stored in a ref-like dependency list via `deps`, so callers pass the
 * service function plus any values the request depends on (for example a referral id).
 */
export function useApiData<T>(
  fetcher: (token: string) => Promise<T>,
  deps: unknown[] = [],
  enabled = true
): ApiData<T> {
  const { token } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    const run = async () => {
      if (!token) {
        if (!cancelled) {
          setError('You are not signed in.');
          setLoading(false);
        }
        return;
      }
      try {
        const result = await fetcher(token);
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Request failed');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, enabled, reloadToken, ...deps]);

  return { data, loading, error, refresh };
}
