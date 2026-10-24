import { useState, useEffect, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/Toast';

interface ManagedUser {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'lecturer' | 'advisor' | 'admin';
  enrolmentStatus: string;
}

interface StudentRecord {
  student_id: string;
  first_name: string;
  surname: string;
  institutional_email: string;
  enrolment_status: string;
}

export default function UsersPage() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(() => (location.state as { globalSearch?: string } | null)?.globalSearch || '');
  const [loadError, setLoadError] = useState('');
  const [staffName, setStaffName] = useState('');
  const [staffEmail, setStaffEmail] = useState('');
  const [staffRole, setStaffRole] = useState<'lecturer' | 'advisor'>('lecturer');
  const [provisioning, setProvisioning] = useState(false);
  const [provisionError, setProvisionError] = useState('');
  const [provisionSuccess, setProvisionSuccess] = useState('');

  useEffect(() => {
    const globalSearch = (location.state as { globalSearch?: string } | null)?.globalSearch;
    if (globalSearch) setQuery(globalSearch);
  }, [location.state]);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        // Fetch all students from LMS (paginated)
        const allStudents: StudentRecord[] = [];
        let offset = 0;
        const limit = 100;
        let hasMore = true;

        while (hasMore) {
          const response = await api.get<{ items: StudentRecord[]; total: number }>(
            `/lms/students?limit=${limit}&offset=${offset}`,
            token || undefined
          );
          
          if (response.items && response.items.length > 0) {
            allStudents.push(...response.items);
            offset += limit;
            hasMore = allStudents.length < response.total;
          } else {
            hasMore = false;
          }
        }

        // Convert students to ManagedUser format
        const managedUsers: ManagedUser[] = allStudents.map((student) => ({
          id: student.student_id,
          name: `${student.first_name} ${student.surname}`,
          email: student.institutional_email,
          role: 'student',
          enrolmentStatus: student.enrolment_status || 'Not recorded'
        }));

        setUsers(managedUsers);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Could not load students';
        setLoadError(message);
        showToast(message, 'error');
        setUsers([]);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, [token, showToast]);

  const provisionStaffAccount = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setProvisionError('');
    setProvisionSuccess('');
    setProvisioning(true);
    try {
      const result = await api.post<{ message: string }>(
        '/admin/users/provision',
        { name: staffName, email: staffEmail, role: staffRole },
        token || undefined
      );
      setProvisionSuccess(result.message);
      setStaffName('');
      setStaffEmail('');
      showToast(result.message, 'success');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not provision the staff account.';
      setProvisionError(message);
      showToast(message, 'error');
    } finally {
      setProvisioning(false);
    }
  };

  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(query.toLowerCase()) ||
      u.email.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-b border-ns-border pb-4"
      >
        <h1 className="text-2xl font-semibold text-ink">User Management</h1>
      </motion.div>

      {loadError && <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-ns-danger">Student list unavailable: {loadError}</div>}

      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-5"
        aria-labelledby="provision-staff-heading"
      >
        <h2 id="provision-staff-heading" className="text-lg font-semibold text-ink">Provision staff account</h2>
        <p className="mt-1 text-sm text-ink-soft">Reserve a lecturer or advisor role for an email address. The account holder must create a Firebase account and verify that same address before signing in.</p>
        <form onSubmit={provisionStaffAccount} className="mt-4 grid gap-3 md:grid-cols-4">
          <label className="text-sm font-medium text-ink">
            Full name
            <input
              required
              maxLength={200}
              value={staffName}
              onChange={(event) => setStaffName(event.target.value)}
              className="neo-input mt-1"
              autoComplete="name"
            />
          </label>
          <label className="text-sm font-medium text-ink">
            Email
            <input
              type="email"
              required
              value={staffEmail}
              onChange={(event) => setStaffEmail(event.target.value)}
              className="neo-input mt-1"
              autoComplete="email"
            />
          </label>
          <label className="text-sm font-medium text-ink">
            Role
            <select
              value={staffRole}
              onChange={(event) => setStaffRole(event.target.value as 'lecturer' | 'advisor')}
              className="neo-input mt-1"
            >
              <option value="lecturer">Lecturer</option>
              <option value="advisor">Advisor</option>
            </select>
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={provisioning}
              className="min-h-11 w-full rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {provisioning ? 'Reserving role…' : 'Reserve staff role'}
            </button>
          </div>
        </form>
        {provisionError && <p className="mt-3 text-sm text-ns-danger" role="alert">{provisionError}</p>}
        {provisionSuccess && <p className="mt-3 text-sm text-emerald-700" role="status">{provisionSuccess}</p>}
      </motion.section>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="neo-card p-5"
      >
        <div className="flex items-center rounded bg-white border border-ns-border px-4 py-2.5">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search users…"
            className="bg-transparent text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none w-full"
          />
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="neo-card p-6"
      >
        <div className="overflow-x-auto -mx-2 px-2">
          <table className="ns-table min-w-[640px]">
            <caption className="sr-only">Imported student records and university enrolment status</caption>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-ink-faint border-b border-brand-100/50">
                <th scope="col" className="pb-3 pr-4">User</th>
                <th scope="col" className="pb-3 pr-4">Email</th>
                <th scope="col" className="pb-3 pr-4">Role</th>
                <th scope="col" className="pb-3 pr-4">Enrolment</th>
                <th scope="col" className="pb-3">Profile</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full"></div>
                      <span className="text-ink-soft">Loading users…</span>
                    </div>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center">
                    <span className="text-ink-soft">
                      {query ? 'No users match your search' : 'No users found'}
                    </span>
                  </td>
                </tr>
              ) : (
                filtered.map((u, i) => (
                  <motion.tr
                    key={u.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-b border-brand-100/30 last:border-0"
                  >
                    <td className="py-3.5 pr-4 font-medium text-ink">
                      {u.name}
                    </td>
                    <td className="py-3.5 pr-4 text-ink-soft">{u.email}</td>
                    <td className="py-3.5 pr-4">
                      <span className="neo-chip bg-ns-surface-secondary text-ns-text-secondary">{u.role}</span>
                    </td>
                    <td className="py-3.5 pr-4">
                      <span className={`neo-chip ${u.enrolmentStatus.toUpperCase() === 'ACTIVE' ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-600'}`}>
                        {u.enrolmentStatus.replace(/_/g, ' ').toLowerCase()}
                      </span>
                    </td>
                    <td className="py-3.5">
                      <div className="flex gap-2">
                        <button
                          onClick={() => navigate(`/admin/students/${u.id}`)}
                          className="min-h-11 rounded border border-ns-border bg-white px-3 text-sm font-medium text-ns-text-secondary hover:bg-ns-surface-secondary transition-colors"
                          title="View student profile"
                          aria-label={`View ${u.name} profile`}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <footer className="mt-3 border-t border-ns-divider pt-3 text-xs text-ns-text-muted">
          Imported student records. Staff accounts must be provisioned above; they are not created from imported student records.
        </footer>
      </motion.div>
    </div>
  );
}
