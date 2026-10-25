import { useEffect, useState, type FormEvent } from 'react';
import { BookOpen, FileUp, Link2, Plus, Save } from 'lucide-react';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface ModuleOption { id: string; module_name: string; module_code: string }
interface TopicOption { id: string; name: string; description: string | null }
interface StudentOption { id: string; name: string; student_number: string }
interface SupportContext {
  academic_average: number | null;
  attendance_recent: number | null;
  attendance_previous: number | null;
  attendance_change: number | null;
  learning_gaps: string[];
  support_suggestion: string | null;
}

export default function LearningSupport() {
  const { token } = useAuth();
  const [modules, setModules] = useState<ModuleOption[]>([]);
  const [topics, setTopics] = useState<TopicOption[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [supportContext, setSupportContext] = useState<SupportContext | null>(null);
  const [moduleId, setModuleId] = useState('');
  const [topicId, setTopicId] = useState('');
  const [studentId, setStudentId] = useState('');
  const [topicName, setTopicName] = useState('');
  const [topicDescription, setTopicDescription] = useState('');
  const [strengths, setStrengths] = useState('');
  const [gaps, setGaps] = useState('');
  const [feedback, setFeedback] = useState('');
  const [goal, setGoal] = useState('');
  const [goalDate, setGoalDate] = useState('');
  const [resourceTitle, setResourceTitle] = useState('');
  const [resourceDescription, setResourceDescription] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');
  const [resourceFile, setResourceFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.get<ModuleOption[]>('/learning/modules', token)
      .then((result) => {
        setModules(result);
        setModuleId((current) => current || result[0]?.id || '');
      })
      .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Modules could not be loaded.'));
  }, [token]);

  useEffect(() => {
    if (!token || !moduleId) return;
    Promise.all([
      api.get<TopicOption[]>(`/learning/modules/${moduleId}/topics`, token),
      api.get<StudentOption[]>(`/learning/modules/${moduleId}/students`, token)
    ]).then(([topicRows, studentRows]) => {
      setTopics(topicRows);
      setTopicId((current) => topicRows.some((topic) => topic.id === current) ? current : topicRows[0]?.id || '');
      setStudents(studentRows);
      setStudentId((current) => studentRows.some((student) => student.id === current) ? current : studentRows[0]?.id || '');
    }).catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Module data could not be loaded.'));
  }, [token, moduleId]);

  useEffect(() => {
    if (!token || !moduleId || !studentId) {
      setSupportContext(null);
      return;
    }
    api.get<SupportContext>(`/students/${studentId}/support-context?module_id=${encodeURIComponent(moduleId)}`, token)
      .then(setSupportContext)
      .catch((requestError: unknown) => setError(requestError instanceof Error ? requestError.message : 'Student support context could not be loaded.'));
  }, [token, moduleId, studentId]);

  const run = async (action: () => Promise<void>, successMessage: string) => {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(successMessage);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The change could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const createTopic = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !moduleId) return;
    await run(async () => {
      await api.post('/learning/topics', { module_id: moduleId, name: topicName, description: topicDescription || null }, token);
      const refreshed = await api.get<TopicOption[]>(`/learning/modules/${moduleId}/topics`, token);
      setTopics(refreshed);
      setTopicId(refreshed.find((topic) => topic.name === topicName.trim())?.id || refreshed[0]?.id || '');
      setTopicName('');
      setTopicDescription('');
    }, 'Topic added to the selected module.');
  };

  const submitFeedback = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !studentId || !topicId) return;
    await run(async () => {
      await api.post('/learning/feedback', {
        student_id: studentId,
        topic_id: topicId,
        strengths: strengths.split(',').map((value) => value.trim()).filter(Boolean),
        learning_gaps: gaps.split(',').map((value) => value.trim()).filter(Boolean),
        feedback,
        learning_goal: goal || null,
        goal_due_date: goalDate || null
      }, token);
      setFeedback('');
      setStrengths('');
      setGaps('');
      setGoal('');
      setGoalDate('');
    }, 'Topic feedback and the learning goal were recorded.');
  };

  const addResource = async (event: FormEvent) => {
    event.preventDefault();
    if (!token || !topicId) return;
    await run(async () => {
      if (resourceFile) {
        const query = new URLSearchParams({ topic_id: topicId, title: resourceTitle });
        if (resourceDescription) query.set('description', resourceDescription);
        const form = new FormData();
        form.append('file', resourceFile);
        await api.postForm(`/learning/resources/upload?${query}`, form, token);
      } else {
        await api.post('/learning/resources/link', {
          topic_id: topicId,
          title: resourceTitle,
          description: resourceDescription || null,
          url: resourceUrl
        }, token);
      }
      setResourceTitle('');
      setResourceDescription('');
      setResourceUrl('');
      setResourceFile(null);
    }, 'Resource linked to the topic.');
  };

  return (
    <div className="space-y-5">
      <header className="neo-card p-6">
        <div className="flex items-center gap-3"><BookOpen className="text-brand-800" /><div><h1 className="text-2xl font-bold text-ink">Topic-level learning support</h1><p className="text-sm text-ink-soft">Record specific strengths and learning gaps; recommendations use resources attached to the selected topic.</p></div></div>
        <label className="mt-4 block max-w-xl text-sm font-medium">Module<select className="neo-input mt-1" value={moduleId} onChange={(event) => setModuleId(event.target.value)}><option value="">Select a module</option>{modules.map((module) => <option key={module.id} value={module.id}>{module.module_code} · {module.module_name}</option>)}</select></label>
      </header>

      {error && <p role="alert" className="text-sm text-ns-danger">{error}</p>}
      {notice && <p role="status" className="text-sm text-ns-success">{notice}</p>}

      <div className="grid gap-5 lg:grid-cols-2">
        <form onSubmit={(event) => void createTopic(event)} className="neo-card space-y-3 p-5">
          <h2 className="font-semibold">Add a module topic</h2>
          <input className="neo-input" required minLength={2} maxLength={160} value={topicName} onChange={(event) => setTopicName(event.target.value)} placeholder="Topic name" />
          <textarea className="neo-input" rows={3} maxLength={2000} value={topicDescription} onChange={(event) => setTopicDescription(event.target.value)} placeholder="Optional topic description" />
          <button className="neo-btn inline-flex items-center gap-2 px-4 py-2 text-sm" disabled={saving || !moduleId}><Plus size={16} />Add topic</button>
        </form>

        <form onSubmit={(event) => void submitFeedback(event)} className="neo-card space-y-3 p-5">
          <h2 className="font-semibold">Record lecturer feedback</h2>
          <label className="block text-sm">Student<select className="neo-input mt-1" value={studentId} onChange={(event) => setStudentId(event.target.value)} required><option value="">Select a student</option>{students.map((student) => <option key={student.id} value={student.id}>{student.name} · {student.student_number}</option>)}</select></label>
          <label className="block text-sm">Topic<select className="neo-input mt-1" value={topicId} onChange={(event) => setTopicId(event.target.value)} required><option value="">Select a topic</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.name}</option>)}</select></label>
          <input className="neo-input" value={strengths} onChange={(event) => setStrengths(event.target.value)} placeholder="Strengths (comma-separated)" />
          <input className="neo-input" required value={gaps} onChange={(event) => setGaps(event.target.value)} placeholder="Specific learning gaps (comma-separated)" />
          <textarea className="neo-input" required minLength={5} maxLength={2000} rows={3} value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Feedback for the student" />
          <input className="neo-input" value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Personal learning goal (optional)" />
          <label className="block text-sm">Goal date<input className="neo-input mt-1" type="date" value={goalDate} onChange={(event) => setGoalDate(event.target.value)} /></label>
          <button className="neo-btn inline-flex items-center gap-2 px-4 py-2 text-sm" disabled={saving || !studentId || !topicId}><Save size={16} />Save feedback</button>
        </form>

        {supportContext && <section className="neo-card space-y-3 p-5 lg:col-span-2" aria-labelledby="support-context-heading">
          <h2 id="support-context-heading" className="font-semibold">Recorded support context</h2>
          <p className="text-xs text-ink-soft">These are recorded indicators for this module, not an automated risk label. Attendance alone does not trigger a support classification.</p>
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded border border-ns-border px-3 py-2">Assessment average: {supportContext.academic_average == null ? 'No recorded marks' : `${supportContext.academic_average}%`}</span>
            <span className="rounded border border-ns-border px-3 py-2">Attendance last 30 days: {supportContext.attendance_recent == null ? 'No records' : `${supportContext.attendance_recent}%`}</span>
            <span className="rounded border border-ns-border px-3 py-2">Change vs previous 30 days: {supportContext.attendance_change == null ? 'Not enough recorded data' : `${supportContext.attendance_change > 0 ? '+' : ''}${supportContext.attendance_change} points`}</span>
          </div>
          {supportContext.learning_gaps.length > 0 && <p className="text-sm"><strong>Lecturer-identified gaps:</strong> {supportContext.learning_gaps.join(', ')}</p>}
          {supportContext.support_suggestion && <p className="border-l-2 border-brand-500 pl-3 text-sm text-ink-soft">{supportContext.support_suggestion}</p>}
        </section>}

        <form onSubmit={(event) => void addResource(event)} className="neo-card space-y-3 p-5 lg:col-span-2">
          <h2 className="font-semibold">Assign a learning resource</h2>
          <label className="block text-sm">Topic<select className="neo-input mt-1" value={topicId} onChange={(event) => setTopicId(event.target.value)} required><option value="">Select a topic</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.name}</option>)}</select></label>
          <input className="neo-input" required minLength={2} maxLength={200} value={resourceTitle} onChange={(event) => setResourceTitle(event.target.value)} placeholder="Resource title" />
          <textarea className="neo-input" rows={2} maxLength={1000} value={resourceDescription} onChange={(event) => setResourceDescription(event.target.value)} placeholder="What will this resource help the student practise?" />
          <label className="block text-sm">Link to an external resource<input className="neo-input mt-1" type="url" value={resourceUrl} onChange={(event) => { setResourceUrl(event.target.value); if (event.target.value) setResourceFile(null); }} placeholder="https://…" /></label>
          <label className="block text-sm">Or upload a document (PDF, Office, text or Markdown; up to 10 MB)<input className="neo-input mt-1" type="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.txt,.md" onChange={(event) => { setResourceFile(event.target.files?.[0] || null); if (event.target.files?.[0]) setResourceUrl(''); }} /></label>
          <button className="neo-btn inline-flex items-center gap-2 px-4 py-2 text-sm" disabled={saving || !topicId || (!resourceFile && !resourceUrl)}>{resourceFile ? <FileUp size={16} /> : <Link2 size={16} />}{resourceFile ? 'Upload resource' : 'Assign link'}</button>
        </form>
      </div>
    </div>
  );
}
