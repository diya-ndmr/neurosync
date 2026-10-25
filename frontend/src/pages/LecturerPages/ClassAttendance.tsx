import { useEffect, useState, type FormEvent } from 'react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ModuleOption { id: string; module_name: string; module_code: string }
interface StudentOption { id: string; name: string; student_number: string }
interface AttendanceRow { id: string; student_id: string; student_name: string; class_name: string; date: string; status: string }
type AttendanceStatus = 'present' | 'absent' | 'late' | 'excused' | 'approved_leave';

export default function ClassAttendance() {
  const { token } = useAuth();
  const [modules, setModules] = useState<ModuleOption[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [records, setRecords] = useState<AttendanceRow[]>([]);
  const [moduleId, setModuleId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [className, setClassName] = useState('');
  const [classDate, setClassDate] = useState(new Date().toISOString().slice(0, 10));
  const [attendanceStatus, setAttendanceStatus] = useState<AttendanceStatus>('present');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshRecords = async (selectedModule: string) => {
    if (!token || !selectedModule) return;
    const [roster, rows] = await Promise.all([
      api.get<StudentOption[]>(`/learning/modules/${selectedModule}/students`, token),
      api.get<AttendanceRow[]>(`/attendance/classes?module_id=${encodeURIComponent(selectedModule)}`, token)
    ]);
    setStudents(roster);
    setStudentId((current) => roster.some((student) => student.id === current) ? current : roster[0]?.id || '');
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
    refreshRecords(moduleId).catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Attendance data could not be loaded.'));
  }, [moduleId, token]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !moduleId || !studentId) return;
    setError(null);
    setNotice(null);
    try {
      await api.post('/attendance/classes', {
        student_id: studentId, module_id: moduleId, class_name: className, class_date: classDate, status: attendanceStatus
      }, token);
      setNotice('Class attendance recorded.');
      setClassName('');
      await refreshRecords(moduleId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Attendance could not be recorded.');
    }
  };

  const correctStatus = async (record: AttendanceRow, status: AttendanceStatus) => {
    if (!token) return;
    setError(null);
    try {
      await api.patch(`/attendance/classes/${record.id}`, {
        student_id: record.student_id, module_id: moduleId, class_name: record.class_name, class_date: record.date, status
      }, token);
      setNotice('Attendance correction saved.');
      await refreshRecords(moduleId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Attendance could not be corrected.');
    }
  };

  return <div className="space-y-5">
    <header className="neo-card p-6"><h1 className="text-2xl font-bold text-ink">Class attendance</h1><p className="mt-1 text-sm text-ink-soft">Record and correct class-level attendance. Approved leave is excluded from the student's attendance rate.</p><label className="mt-4 block max-w-xl text-sm font-medium">Module<select className="neo-input mt-1" value={moduleId} onChange={(event) => setModuleId(event.target.value)}><option value="">Select a module</option>{modules.map((module) => <option key={module.id} value={module.id}>{module.module_code} · {module.module_name}</option>)}</select></label></header>
    {error && <p role="alert" className="text-sm text-ns-danger">{error}</p>}
    {notice && <p role="status" className="text-sm text-ns-success">{notice}</p>}
    <form onSubmit={(event) => void submit(event)} className="neo-card grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-5">
      <label className="text-sm">Student<select className="neo-input mt-1" value={studentId} onChange={(event) => setStudentId(event.target.value)} required><option value="">Select student</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name} · {student.student_number}</option>)}</select></label>
      <label className="text-sm">Class<input className="neo-input mt-1" required value={className} onChange={(event) => setClassName(event.target.value)} placeholder="e.g. Lecture 4" /></label>
      <label className="text-sm">Date<input className="neo-input mt-1" type="date" required value={classDate} onChange={(event) => setClassDate(event.target.value)} /></label>
      <label className="text-sm">Status<select className="neo-input mt-1" value={attendanceStatus} onChange={(event) => setAttendanceStatus(event.target.value as AttendanceStatus)}><option value="present">Present</option><option value="absent">Absent</option><option value="late">Late</option><option value="excused">Excused</option><option value="approved_leave">Approved leave</option></select></label>
      <button className="neo-btn self-end px-4 py-2.5 text-sm" disabled={!moduleId || !studentId}>Record attendance</button>
    </form>
    <section className="neo-card p-5"><h2 className="mb-3 font-semibold">Recent records</h2>{records.length === 0 ? <p className="text-sm text-ink-faint">No class attendance has been recorded for this module.</p> : <div className="overflow-x-auto"><table className="ns-table"><thead><tr><th scope="col">Student</th><th scope="col">Date</th><th scope="col">Class</th><th scope="col">Status / correction</th></tr></thead><tbody>{records.map((record) => <tr key={record.id}><td>{record.student_name}</td><td>{record.date}</td><td>{record.class_name}</td><td><select aria-label={`Attendance status for ${record.student_name} ${record.class_name}`} className="neo-input min-w-40" value={record.status} onChange={(event) => void correctStatus(record, event.target.value as AttendanceStatus)}><option value="present">Present</option><option value="absent">Absent</option><option value="late">Late</option><option value="excused">Excused</option><option value="approved_leave">Approved leave</option></select></td></tr>)}</tbody></table></div>}</section>
  </div>;
}
