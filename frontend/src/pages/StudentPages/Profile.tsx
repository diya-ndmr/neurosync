import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import LoadingState from '../../components/LoadingState';
import DataSourceNotice from '../../components/DataSourceNotice';
import { useAuth } from '../../context/AuthContext';
import { useApiData } from '../../hooks/useApiData';
import { fetchMyStudentProfile } from '../../services/liveData';
import { initials, formatDate } from '../../utils/helpers';
import { createStudentDemoProfile } from '../../services/studentDemoData';

export default function Profile() {
  const { user } = useAuth();
  const fallback = useMemo(() => ({ data: createStudentDemoProfile(user) }), [user]);
  const { data: student, loading, error, source } = useApiData(fetchMyStudentProfile, [], true, fallback);

  if (loading) return <LoadingState label="Loading your profile…" />;
  if (error) return <div role="alert" className="neo-card p-6 text-sm text-ns-danger">Your profile could not be loaded: {error}</div>;
  if (!student) return <div role="alert" className="neo-card p-6 text-sm text-ns-danger">Your student profile is not available.</div>;

  const fullName = user?.name || `${student.first_name} ${student.surname}`;

  return (
    <div className="space-y-6">
      <DataSourceNotice source={source} />
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-800">Account profile</p>
        <h1 className="mt-1 text-2xl font-extrabold text-ink">Settings &amp; preferences</h1>
        <p className="mt-1 text-sm text-ink-soft">Your student profile and university record</p>
      </div>

      <nav aria-label="Profile settings" className="flex gap-2 overflow-x-auto border-b border-ns-border">
        <span aria-current="page" className="shrink-0 border-b-2 border-brand-700 px-4 py-3 text-sm font-semibold text-brand-800">
          Account profile
        </span>
        <Link to="/student/settings" className="shrink-0 border-b-2 border-transparent px-4 py-3 text-sm font-medium text-ink-soft hover:border-ns-border hover:text-ink">
          Preferences
        </Link>
      </nav>

      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-6 md:p-8"
        aria-labelledby="personal-information-heading"
      >
        <div className="flex flex-col gap-5 border-b border-ns-divider pb-6 sm:flex-row sm:items-center">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-brand-700 text-2xl font-bold text-white shadow-sm">
            {initials(fullName)}
          </div>
          <div className="min-w-0">
            <h2 className="text-xl font-extrabold text-ink">{fullName}</h2>
            <p className="mt-1 text-sm text-ink-soft">{student.programme || 'Programme not recorded'}{student.year_level > 0 ? ` · Year ${student.year_level}` : ''}</p>
            <p className="mt-1 text-sm text-ink-faint">Student ID: {student.student_number}</p>
            <p className="mt-2 text-xs text-ink-faint">Member since {formatDate(student.created_at)}</p>
          </div>
          <span className="neo-chip w-fit bg-ns-surface-secondary text-ns-text-secondary capitalize sm:ml-auto">{user?.role || 'student'}</span>
        </div>

        <div className="pt-6">
          <h2 id="personal-information-heading" className="text-lg font-bold text-ink">Personal information</h2>
          <p className="mt-1 text-sm text-ink-soft">Details currently available from your university record</p>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
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
        </div>
      </motion.section>
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-ns-border bg-white p-3">
    <p className="text-xs font-semibold text-ink-faint">{label}</p>
    <p className="mt-2 break-words text-sm font-medium text-ink">{value}</p>
  </div>;
}
