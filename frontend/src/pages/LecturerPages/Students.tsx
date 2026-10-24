import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, AlertTriangle, Eye, MessageSquarePlus, LoaderCircle } from 'lucide-react';
import { api } from '../../services/api';
import { riskBg } from '../../utils/helpers';
import { useAuth } from '../../context/AuthContext';
import type { LmsStudentSummary } from '../../types';

export default function Students() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState(() => (location.state as { globalSearch?: string } | null)?.globalSearch || '');
  const [riskFilter, setRiskFilter] = useState<'all' | 'LOW' | 'MEDIUM' | 'HIGH'>('all');
  const [students, setStudents] = useState<LmsStudentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const globalSearch = (location.state as { globalSearch?: string } | null)?.globalSearch;
    if (globalSearch) setQuery(globalSearch);
  }, [location.state]);

  useEffect(() => {
    let active = true;
    api.get<{ items: LmsStudentSummary[] }>('/workflow/lecturer/students', token || undefined)
      .then((response) => { if (active) setStudents(response.items); })
      .catch((requestError: Error) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  const filtered = students.filter((student) => {
    const matchesQuery = `${student.name} ${student.student_id} ${student.modules.map((module) => module.module_code).join(' ')}`.toLowerCase().includes(query.toLowerCase());
    const matchesRisk = riskFilter === 'all' || student.risk.risk_level === riskFilter;
    return matchesQuery && matchesRisk;
  });

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="neo-card p-7"
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center text-brand-800">
            <AlertTriangle size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-ink">My students</h1>
            <p className="text-sm text-ink-soft">LMS academic indicators within your teaching scope</p>
          </div>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="neo-card p-5 flex flex-wrap items-center gap-3"
      >
        <div className="flex items-center gap-2 rounded-lg bg-white border border-ns-border px-4 py-2.5 flex-1 min-w-[200px]">
          <Search size={18} className="text-ink-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or student number…"
            className="bg-transparent text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none w-full"
          />
        </div>
        <div className="flex gap-2">
          {(['all', 'LOW', 'MEDIUM', 'HIGH'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setRiskFilter(f)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                riskFilter === f
                  ? 'bg-brand-700 text-white'
                  : 'bg-white text-ink-soft border border-ns-border'
              }`}
            >
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Table */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="neo-card p-6"
      >
        <div className="overflow-x-auto -mx-2 px-2">
          <table className="ns-table min-w-[760px]">
            <caption className="sr-only">LMS students, academic indicators, risk explanations, and available actions</caption>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wider text-ink-faint border-b border-brand-100/50">
                <th scope="col" className="pb-3 pr-4">Student</th>
                <th scope="col" className="pb-3 pr-4">Number</th>
                <th scope="col" className="pb-3 pr-4">Module</th>
                <th scope="col" className="pb-3 pr-4">Avg Mark</th>
                <th scope="col" className="pb-3 pr-4">Attendance</th>
                <th scope="col" className="pb-3 pr-4">Risk</th>
                <th scope="col" className="pb-3 pr-4">AI Explanation</th>
                <th scope="col" className="pb-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <motion.tr
                  key={s.student_id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
                  className="border-b border-brand-100/30 last:border-0"
                >
                  <td className="py-3.5 pr-4 font-semibold text-ink">{s.name}</td>
                  <td className="py-3.5 pr-4 text-ink-soft">{s.student_id}</td>
                  <td className="py-3.5 pr-4 text-ink-soft">{s.modules.map((module) => module.module_code).join(', ')}</td>
                  <td className="py-3.5 pr-4 font-bold text-ink">{s.metrics.academic_average}%</td>
                  <td className="py-3.5 pr-4">
                    <span className={s.metrics.attendance < 70 ? 'text-red-500 font-bold' : 'text-ink-soft'}>
                      {s.metrics.attendance}%
                    </span>
                  </td>
                  <td className="py-3.5 pr-4">
                    <span className={`neo-chip ${riskBg(s.risk.risk_level)}`}>{s.risk.risk_level}</span>
                  </td>
                  <td className="py-3.5 pr-4 text-xs text-ink-soft max-w-[220px]">{s.risk.evidence[0]}</td>
                  <td className="py-3.5">
                    <div className="flex gap-2">
                      <button
                        onClick={() => navigate(`/lecturer/students/${s.student_id}`)}
                        className="min-h-11 min-w-11 rounded-lg bg-white border border-ns-border flex items-center justify-center text-brand-800 hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500"
                        title="Review LMS profile"
                        aria-label={`Review ${s.name}`}
                      >
                        <Eye size={15} />
                      </button>
                      <button
                        onClick={() => navigate(`/lecturer/students/${s.student_id}?refer=1`)}
                        className="min-h-11 min-w-11 rounded-lg bg-white border border-ns-border flex items-center justify-center text-brand-800 hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500"
                        title="Refer to academic advisor"
                        aria-label={`Refer ${s.name} to an advisor`}
                      >
                        <MessageSquarePlus size={15} />
                      </button>
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>

        {loading && <div className="flex items-center justify-center gap-2 py-10 text-sm text-ink-soft"><LoaderCircle className="animate-spin" size={18} />Loading authorised LMS students…</div>}
        {error && <div role="alert" className="py-5 text-sm text-ns-danger">{error}</div>}
        {!loading && !error && filtered.length === 0 && (
          <div className="neo-card px-6 py-12 text-center text-ink-faint text-sm">
            No students match your filters. Try “All” or clear the search.
          </div>
        )}
      </motion.div>
    </div>
  );
}

