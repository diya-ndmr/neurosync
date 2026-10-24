import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/api';
import {
  fetchAdminAnalytics,
  fetchLecturerDashboard,
  fetchStudentDashboard
} from '../services/liveData';
import { adminAnalytics, lecturerDashboard, studentDashboard } from '../services/mockData';
import type { AdminAnalytics, LecturerDashboardData, Role, StudentDashboardData } from '../types';

type DataMap = {
  student: StudentDashboardData;
  lecturer: LecturerDashboardData;
  advisor: never;
  admin: AdminAnalytics;
};

const offlineData: Omit<DataMap, 'advisor'> = {
  student: studentDashboard,
  lecturer: lecturerDashboard,
  admin: adminAnalytics
};

const loaders: Record<'student' | 'lecturer' | 'admin', (token: string) => Promise<unknown>> = {
  student: fetchStudentDashboard,
  lecturer: fetchLecturerDashboard,
  admin: fetchAdminAnalytics
};

export interface DashboardData<T> {
  data: T | null;
  loading: boolean;
  /** Set when the live request was rejected; `data` then falls back to demo values. */
  error: string | null;
  source: 'live' | 'offline-demo' | null;
  refresh: () => void;
}

/**
 * Loads the signed-in user's dashboard from the API.
 *
 * The offline demo dataset is only used when the backend cannot be reached at all
 * (the same rule the login screen follows) — a rejected request surfaces an error
 * instead of quietly showing invented numbers. `refresh` re-runs the request so a
 * page can pick up a new referral, intervention or intervention comparison.
 */
export function useDashboardData<T>(role: Role, refreshKey: unknown = null): DashboardData<T> {
  const { token } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<'live' | 'offline-demo' | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const refresh = useCallback(() => setReloadToken((value) => value + 1), []);

  useEffect(() => {
    if (role === 'advisor') {
      // The advisor dashboard has its own live hook in the advisor pages.
      setData(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const run = async () => {
      if (token) {
        try {
          const live = (await loaders[role](token)) as T;
          if (cancelled) return;
          setData(live);
          setSource('live');
          return;
        } catch (err) {
          if (cancelled) return;
          if (err instanceof ApiError) {
            setError(err.message);
            setData(null);
            setSource(null);
            return;
          }
          // Network failure: fall through to the offline demo dataset.
        }
      }
      if (cancelled) return;
      setData(offlineData[role] as unknown as T);
      setSource('offline-demo');
    };

    void run().finally(() => {
      if (!cancelled) setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [role, token, reloadToken, refreshKey]);

  return { data, loading, error, source, refresh };
}


