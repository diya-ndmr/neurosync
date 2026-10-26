import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ModuleOption { id: string; module_name: string; module_code: string }
interface StudentOption { id: string; name: string; student_number: string }
interface AttendanceRow { id: string; student_id: string; student_name: string; class_name: string; date: string; status: string }
type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused' | 'approved_leave';
type RegisterDraft = { session: string; statuses: Record<string, AttendanceStatus> };

const statusOptions: { value: AttendanceStatus; label: string }[] = [
  { value: 'present', label: 'Present' },
  { value: 'absent', label: 'Absent' },
  { value: 'late', label: 'Late' },
  { value: 'excused', label: 'Excused' },
  { value: 'approved_leave', label: 'Approved leave' }
];

export default function ClassAttendance() {
  const { token } = useAuth();
  const [modules, setModules] = useState<ModuleOption[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [records, setRecords] = useState<AttendanceRow[]>([]);
  const [moduleId, setModuleId] = useState('');
  const [className, setClassName] = useState('');
  const [classDate, setClassDate] = useState(new Date().toISOString().slice(0, 10));
  const [bulkStatus, setBulkStatus] = useState<AttendanceStatus>('present');
  const [draft, setDraft] = useState<RegisterDraft>({ session: '', statuses: {} });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshRecords = async (selectedModule: string) => {
    if (!token || !selectedModule) return;
    const [roster, rows] = await Promise.all([
      api.get<StudentOption[]>(`/learning/modules/${selectedModule}/students`, token),
      api.get<AttendanceRow[]>(`/attendance/classes?module_id=${encodeURIComponent(selectedModule)}`, token)
    ]);
    setStudents(roster);
    setRecords(rows);
  };

  useEffect(() => {
    if (!token) return;
    api.get<ModuleOption[]>('/learning/modules', token).then((result) => {
      setModules(result);
      setModuleId((current) => current || result[0]?.id || '');
    }).catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Modules could not be loaded.'));
  }, [token]);

  useEffect(() => {
    if (!moduleId) return;
    setError(null);
    refreshRecords(moduleId).catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Attendance data could not be loaded.'));
  }, [moduleId, token]);

  const sessionKey = `${moduleId}|${classDate}|${className.trim()}`;
  const savedByStudent = new Map(
    records
      .filter((record) => record.date === classDate && record.class_name === className.trim())
      .map((record) => [record.student_id, record])
  );
  const statusFor = (studentId: string): AttendanceStatus => {
    const override = draft.session === sessionKey ? draft.statuses[studentId] : undefined;
    return override ?? (savedByStudent.get(studentId)?.status as AttendanceStatus | undefined) ?? 'present';
  };
  const markedCount = students.filter((student) => savedByStudent.has(student.id)).length;

  const setStudentStatus = (studentId: string, status: AttendanceStatus) => {
    setDraft((current) => ({
      session: sessionKey,
      statuses: { ...(current.session === sessionKey ? current.statuses : {}), [studentId]: status }
    }));
  };

  const saveRegister = async () => {
    if (!token || !moduleId || !className.trim() || students.length === 0) return;
    setSaving(true);
    setError(null);
    setNotice(null);

    let savedCount = 0;
    const failures: string[] = [];
    for (let start = 0; start < students.length; start += 8) {
      const batch = students.slice(start, start + 8);
      const results = await Promise.all(batch.map(async (student) => {
        const status = statusFor(student.id);
        const existing = savedByStudent.get(student.id);
        if (existing?.status === status) return { student: student.name, saved: false };
        try {
          if (existing) {
            await api.patch(`/attendance/classes/${existing.id}`, {
              student_id: student.id,
              module_id: moduleId,
              class_name: className.trim(),
              class_date: classDate,
              status
            }, token);
          } else {
            await api.post('/attendance/classes', {
              student_id: student.id,
              module_id: moduleId,
              class_name: className.trim(),
              class_date: classDate,
              status
            }, token);
          }
          return { student: student.name, saved: true };
        } catch (requestError) {
          return {
            student: student.name,
            saved: false,
            error: requestError instanceof Error ? requestError.message : 'Request failed'
          };
        }
      }));

      savedCount += results.filter((result) => result.saved).length;
      failures.push(...results.filter((result) => 'error' in result).map((result) => `${result.student}: ${result.error}`));
    }

    try {
      await refreshRecords(moduleId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The register was saved, but attendance records could not be refreshed.');
      setSaving(false);
      return;
    }
    setDraft({ session: '', statuses: {} });
    if (failures.length > 0) {
      const details = failures.slice(0, 3).join(' ');
      setError(`${savedCount} student record${savedCount === 1 ? '' : 's'} saved; ${failures.length} failed. ${details}${failures.length > 3 ? ` And ${failures.length - 3} more.` : ''}`);
    } else {
      setNotice(savedCount > 0
        ? `Attendance saved for ${savedCount} student${savedCount === 1 ? '' : 's'}.`
        : 'The register is already up to date.');
    }
    setSaving(false);
  };

  const correctStatus = async (record: AttendanceRow, status: AttendanceStatus) => {
    if (!token) return;
    setError(null);
    setNotice(null);
    try {
      await api.patch(`/attendance/classes/${record.id}`, {
        student_id: record.student_id,
        module_id: moduleId,
        class_name: record.class_name,
        class_date: record.date,
        status
      }, token);
      setNotice('Attendance correction saved.');
      await refreshRecords(moduleId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Attendance could not be corrected.');
    }
  };

  return <div className="space-y-5">
    <header className="neo-card p-6">
      <h1 className="text-2xl font-bold text-ink">Class attendance</h1>
      <label className="mt-4 block max-w-xl text-sm font-medium">
        Module
        <select className="neo-input mt-1" value={moduleId} onChange={(event) => setModuleId(event.target.value)}>
          <option value="">Select a module</option>
          {modules.map((module) => <option key={module.id} value={module.id}>{module.module_code} · {module.module_name}</option>)}
        </select>
      </label>
    </header>

    {error && <p role="alert" className="text-sm text-ns-danger">{error}</p>}
    {notice && <p role="status" className="text-sm text-ns-success">{notice}</p>}

    <section className="neo-card overflow-hidden">
      <div className="grid gap-4 border-b border-ns-border p-5 sm:grid-cols-2">
        <label className="text-sm font-medium">Class<input className="neo-input mt-1" required minLength={2} value={className} onChange={(event) => setClassName(event.target.value)} placeholder="e.g. Lecture 4" /></label>
        <label className="text-sm font-medium">Date<input className="neo-input mt-1" type="date" required value={classDate} onChange={(event) => setClassDate(event.target.value)} /></label>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ns-border bg-ns-surface-secondary/60 p-4">
        <p className="text-sm font-semibold text-ns-text-primary">
          Register <span className="ml-1 text-xs font-normal text-ns-text-muted">{markedCount} / {students.length} saved</span>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="bulk-attendance-status">Status to apply to the whole class</label>
          <select id="bulk-attendance-status" className="neo-input min-h-10 w-auto py-1.5 text-sm" value={bulkStatus} onChange={(event) => setBulkStatus(event.target.value as AttendanceStatus)}>
            {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          <button type="button" className="neo-btn min-h-10 px-3 text-sm" disabled={!students.length} onClick={() => setDraft({ session: sessionKey, statuses: Object.fromEntries(students.map((student) => [student.id, bulkStatus])) })}>
            Apply to all
          </button>
        </div>
      </div>

      {students.length === 0 ? (
        <p className="p-6 text-sm text-ink-faint">{moduleId ? 'No students are enrolled in this module.' : 'Select a module to load its register.'}</p>
      ) : (
        <>
          <div className="max-h-[min(60vh,620px)] overflow-auto">
            <table className="ns-table">
              <thead className="sticky top-0 z-10">
                <tr><th scope="col">Student</th><th scope="col">Student number</th><th scope="col">Status</th></tr>
              </thead>
              <tbody>
                {students.map((student) => {
                  const saved = savedByStudent.has(student.id);
                  return (
                    <tr key={student.id}>
                      <td className="font-medium">{student.name}</td>
                      <td className="font-mono text-xs text-ns-text-muted">{student.student_number}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <select
                            aria-label={`Attendance status for ${student.name}`}
                            className="neo-input min-h-10 min-w-40 py-1.5 text-sm"
                            value={statusFor(student.id)}
                            onChange={(event) => setStudentStatus(student.id, event.target.value as AttendanceStatus)}
                          >
                            {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                          </select>
                          {saved && <span className="text-xs font-medium text-ns-success">Saved</span>}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex justify-end border-t border-ns-border p-4">
            <button type="button" className="neo-btn min-h-11 px-5 text-sm" disabled={saving || !moduleId || className.trim().length < 2 || !classDate} onClick={() => void saveRegister()}>
              {saving ? 'Saving register…' : 'Save register'}
            </button>
          </div>
        </>
      )}
    </section>

    <section className="neo-card p-5">
      <h2 className="mb-3 font-semibold">Recent records</h2>
      {records.length === 0 ? <p className="text-sm text-ink-faint">No class attendance has been recorded for this module.</p> : <div className="overflow-x-auto"><table className="ns-table"><thead><tr><th scope="col">Student</th><th scope="col">Date</th><th scope="col">Class</th><th scope="col">Status / correction</th></tr></thead><tbody>{records.map((record) => <tr key={record.id}><td>{record.student_name}</td><td>{record.date}</td><td>{record.class_name}</td><td><select aria-label={`Attendance status for ${record.student_name} ${record.class_name}`} className="neo-input min-w-40" value={record.status} onChange={(event) => void correctStatus(record, event.target.value as AttendanceStatus)}>{statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}
