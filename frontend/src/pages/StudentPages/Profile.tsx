import { motion } from 'framer-motion';
import LoadingState from '../../components/LoadingState';
import { useAuth } from '../../context/AuthContext';
import { useApiData } from '../../hooks/useApiData';
import { fetchMyStudentProfile } from '../../services/liveData';
import { initials, formatDate } from '../../utils/helpers';

export default function Profile() {
  const { user } = useAuth();
  const { data: student, loading } = useApiData(fetchMyStudentProfile);

  if (loading || !student) return <LoadingState label="Loading your profile…" />;

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <h1 className="text-2xl font-extrabold text-ink">My Profile</h1>
        <p className="text-sm text-ink-soft mt-1">Your university record and currently available contact details</p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile summary */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="neo-card p-6 flex flex-col items-center text-center"
        >
          <div className="w-24 h-24 rounded-xl bg-brand-700 text-white text-3xl font-bold flex items-center justify-center shadow-sm mb-4">
            {initials(user?.name || `${student.first_name} ${student.surname}`)}
          </div>
          <h3 className="text-xl font-extrabold text-ink">{user?.name || `${student.first_name} ${student.surname}`}</h3>
          <p className="text-sm text-ink-faint">{student.student_number}</p>
          <div className="mt-4 w-full space-y-2">
            <div className="neo-chip bg-ns-surface-secondary text-ns-text-secondary w-fit mx-auto capitalize">{user?.role || 'student'}</div>
            <div className="neo-chip bg-ns-surface-secondary text-ns-text-secondary w-fit mx-auto">Year {student.year_level}</div>
          </div>
          <div className="mt-5 w-full rounded-lg bg-ns-surface-secondary border border-ns-border p-4">
            <p className="text-xs text-ink-faint">Member since</p>
            <p className="text-sm font-bold text-ink">{formatDate(student.created_at)}</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="neo-card p-6 lg:col-span-2"
        >
          <h3 className="font-bold text-ink mb-5">University record</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <ProfileField label="First name" value={student.first_name} />
            <ProfileField label="Surname" value={student.surname} />
            <ProfileField label="Email" value={user?.email || 'Not recorded'} />
            <ProfileField label="Student number" value={student.student_number} />
            <ProfileField label="Phone" value="Not recorded" />
            <ProfileField label="Address" value="Not recorded" />
            <div className="sm:col-span-2"><ProfileField label="Programme" value={student.programme} /></div>
          </div>
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
