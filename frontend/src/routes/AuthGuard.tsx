import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import SplashScreen from '../components/Layout/SplashScreen';

export default function AuthGuard() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <SplashScreen />;

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location, reason: 'session-expired' }} />;
  }

  // Redirect users to their role dashboard if they land on a guarded root
  if (location.pathname === '/') {
    const paths: Record<string, string> = {
      student: '/student/dashboard',
      lecturer: '/lecturer/dashboard',
      advisor: '/advisor/dashboard',
      admin: '/admin/dashboard'
    };
    return <Navigate to={paths[user.role]} replace />;
  }

  return <Outlet />;
}

