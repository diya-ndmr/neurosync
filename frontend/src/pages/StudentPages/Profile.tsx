import { motion } from 'framer-motion';
import LoadingState from '../../components/LoadingState';
import { useAuth } from '../../context/AuthContext';
import { useApiData } from '../../hooks/useApiData';
import { fetchMyStudentProfile } from '../../services/liveData';
import { initials, formatDate } from '../../utils/helpers';

export default function Profile() {
  const { user } = useAuth();
  const { data: student, loading, error } = useApiData(fetchMyStudentProfile);

  if (loading) return <LoadingState label="Loading your profile…" />;
  if (error) return <div role="alert" className="neo-card p-6 text-sm text-ns-danger">Your profile could not be loaded: {error}</div>;
  if (!student) return <div role="alert" className="neo-card p-6 text-sm text-ns-danger">Your student profile is not available.</div>;

  const fullName = user?.name || `${student.first_name} ${student.surname}`;

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-6 md:p-7"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">Account profile</p>
        <h1 className="mt-1 text-2xl font-extrabold text-ink">Settings &amp; preferences</h1>
        <p className="mt-1 text-sm text-ink-soft">Your student profile and university record</p>
      </motion.div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="neo-card flex flex-col items-center p-6 text-center"
        >
          <div className="mb-4 flex h-24 w-24 items-center justify-center rounded-2xl bg-brand-700 text-3xl font-bold text-white shadow-sm">
            {initials(fullName)}
          </div>
          <h2 className="text-xl font-extrabold text-ink">{fullName}</h2>
          <p className="mt-1 text-sm text-ink-faint">{student.programme}</p>
          <p className="mt-1 text-sm font-medium text-ink-soft">Student ID: {student.student_number}</p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary capitalize">{user?.role || 'student'}</span>
            <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">
              {student.year_level > 0 ? `Year ${student.year_level}` : 'Year not provided'}
            </span>
          </div>
          <div className="mt-5 w-full rounded-lg bg-ns-surface-secondary border border-ns-border p-4">
            <p className="text-xs font-semibold text-ink-faint">Member since</p>
            <p className="mt-1 text-sm font-bold text-ink">{formatDate(student.created_at)}</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="neo-card p-6 md:p-7 lg:col-span-2"
        >
          <div className="mb-5">
            <h2 className="text-lg font-bold text-ink">Personal information</h2>
            <p className="mt-1 text-sm text-ink-soft">Details currently available from your university record</p>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ProfileField label="Full name" value={fullName} />
            <ProfileField label="University email" value={user?.email || 'Not recorded'} />
            <ProfileField label="Preferred name" value="Not recorded" />
            <ProfileField label="Contact number" value="Not recorded" />
            <ProfileField label="Student ID" value={student.student_number} />
            <ProfileField label="Year of study" value={student.year_level > 0 ? `Year ${student.year_level}` : 'Not provided'} />
            <div className="sm:col-span-2"><ProfileField label="Programme" value={student.programme || 'Not recorded'} /></div>
          </div>
          <p className="mt-5 border-t border-ns-divider pt-4 text-xs text-ink-faint">
            This page displays your current university record. Profile editing is not available here.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3">
    <p className="text-xs font-semibold text-ink-faint">{label}</p>
    <p className="mt-2 break-words text-sm font-medium text-ink">{value}</p>
  </div>;
}
