import { api } from './api';
import type {
  AdminAnalytics,
  LecturerDashboardData,
  Recommendation,
  RiskPrediction,
  StudentDashboardData,
  StudentProfile
} from '../types';

/**
 * Live data access for the role dashboards.
 *
 * Every page used to read `services/mockData.ts`, so the student screen showed
 * numbers that had nothing to do with the signed-in account and the admin screens
 * reported 5 240 students against a 500-student dataset. These functions call the
 * real endpoints and map the responses onto the shapes the existing components
 * already expect, so no component had to be redesigned.
 */

export interface AttendanceRow {
  id: string;
  module: string;
  module_code: string;
  attendance_percentage: number;
  date: string;
}

export interface LmsAssessmentRow {
  id: string;
  module: string;
  module_code: string;
  assessment_type: string;
  mark: number;
  assessment_date: string;
  module_id?: string;
  title?: string;
  topic?: string | null;
  max_score?: number | null;
  status?: string | null;
  feedback?: string | null;
}

export interface SupplementaryAssessmentFeedback {
  assessment_id: string;
  feedback: string | null;
  questions: { question_id: string; is_correct: boolean }[];
  correct_count: number;
  question_count: number;
}

export interface LmsStudySession {
  id: string;
  subject: string;
  duration_minutes: number;
  activity_type: string;
  created_at: string;
}

export interface WellbeingCheckin {
  id: string;
  mood_score: number;
  stress_level: number;
  notes: string | null;
  created_at: string;
}

export interface LearningResource {
  id: string;
  title: string;
  description: string | null;
  resource_type: 'link' | 'file';
  url: string;
  filename: string | null;
  status: 'new' | 'viewed' | 'completed';
  provider: string;
  reviewed_by_lecturer: boolean;
}

export interface LearningSupportItem {
  feedback_id: string;
  topic_id: string;
  module: string;
  topic: string;
  strengths: string[];
  learning_gaps: string[];
  feedback: string;
  learning_goal: string | null;
  goal_due_date: string | null;
  recommendation_explanation: string;
  performance_context: { module_average: number | null; explanation: string };
  resources: LearningResource[];
}

export interface AttendanceSummary {
  period_start: string;
  period_end: string;
  attendance_rate: number | null;
  classes_attended: number;
  classes_counted: number;
  excused_absences: number;
  monthly_breakdown: { month: string; period_start: string; period_end: string; percentage: number | null; attended: number; classes: number }[];
  records: { id: string; module: string; module_code: string; class_name: string; date: string; status: string }[];
}

export interface WellnessReferral {
  id: string;
  status: string;
  student_message: string;
  created_at: string;
}

export interface WellnessSlot {
  id: string;
  starts_at: string;
  duration_minutes: number;
  location: string;
}

export async function fetchMyStudentProfile(token: string): Promise<StudentProfile> {
  return api.get<StudentProfile>('/students/me', token);
}

export async function fetchStudentDashboard(token: string): Promise<StudentDashboardData> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<StudentDashboardData>(`/students/${profile.id}/dashboard`, token);
}

export async function fetchStudentAssessments(token: string): Promise<LmsAssessmentRow[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<LmsAssessmentRow[]>(`/students/${profile.id}/assessments`, token);
}

export async function fetchSupplementaryAssessmentFeedback(token: string): Promise<SupplementaryAssessmentFeedback[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<SupplementaryAssessmentFeedback[]>(
    `/students/${profile.id}/supplementary-assessments`,
    token,
  );
}

export async function fetchStudentAttendance(token: string): Promise<AttendanceRow[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<AttendanceRow[]>(`/students/${profile.id}/attendance`, token);
}

export async function fetchStudentAttendanceSummary(token: string): Promise<AttendanceSummary> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<AttendanceSummary>(`/students/${profile.id}/attendance/summary`, token);
}

export async function fetchLearningSupport(token: string): Promise<LearningSupportItem[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<LearningSupportItem[]>(`/students/${profile.id}/learning-support`, token);
}

export async function fetchStudentStudySessions(token: string): Promise<LmsStudySession[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<LmsStudySession[]>(`/students/${profile.id}/study-sessions`, token);
}

export async function fetchWellbeingHistory(token: string): Promise<WellbeingCheckin[]> {
  const profile = await fetchMyStudentProfile(token);
  return api.get<WellbeingCheckin[]>(`/wellbeing/${profile.id}`, token);
}

export async function fetchAdminAnalytics(token: string): Promise<AdminAnalytics> {
  return api.get<AdminAnalytics>('/admin/analytics', token);
}

export async function fetchRecommendations(token: string): Promise<Recommendation[]> {
  const dashboard = await fetchStudentDashboard(token);
  return dashboard.recommendations ?? [];
}

export async function fetchRisk(token: string): Promise<RiskPrediction | undefined> {
  const dashboard = await fetchStudentDashboard(token);
  return dashboard.risk;
}

interface LecturerRosterItem {
  student_id: string;
  name: string;
  programme: string;
  modules: { module_id: string; module_code: string; module_name: string }[];
  metrics: {
    academic_average: number;
    attendance: number;
    attendance_30d: number;
    attendance_7d: number;
    engagement_score: number;
    missing_submissions: number;
  };
  risk: { risk_level: 'LOW' | 'MEDIUM' | 'HIGH'; risk_score: number; evidence: string[] };
}

const average = (values: number[]) =>
  values.length ? Math.round((values.reduce((total, value) => total + value, 0) / values.length) * 10) / 10 : 0;

/**
 * The lecturer dashboard is derived from the same LMS roster the lecturer workflow
 * screens use, so the numbers on the dashboard and in a student review always agree.
 */
export async function fetchLecturerDashboard(token: string): Promise<LecturerDashboardData> {
  const roster = await api.get<{ items: LecturerRosterItem[] }>('/workflow/lecturer/students', token);
  const students = roster.items ?? [];

  const riskCount = (level: 'LOW' | 'MEDIUM' | 'HIGH') =>
    students.filter((student) => student.risk.risk_level === level).length;

  const moduleMarks = new Map<string, number[]>();
  for (const student of students) {
    const moduleName = student.modules[0]?.module_name ?? 'Unassigned';
    moduleMarks.set(moduleName, [...(moduleMarks.get(moduleName) ?? []), student.metrics.academic_average]);
  }

  const engagementBuckets = [
    { month: 'Last 7 days', values: students.map((student) => student.metrics.attendance_7d) },
    { month: 'Last 30 days', values: students.map((student) => student.metrics.attendance_30d) },
    { month: 'Term to date', values: students.map((student) => student.metrics.attendance) }
  ];

  return {
    total_students: students.length,
    average_mark: average(students.map((student) => student.metrics.academic_average)),
    average_attendance: average(students.map((student) => student.metrics.attendance)),
    students_at_risk: students.filter((student) => student.risk.risk_level !== 'LOW').length,
    risk_distribution: [
      { name: 'LOW', value: riskCount('LOW') },
      { name: 'MEDIUM', value: riskCount('MEDIUM') },
      { name: 'HIGH', value: riskCount('HIGH') }
    ],
    class_performance: engagementBuckets.map((bucket) => ({ month: bucket.month, average: average(bucket.values) })),
    module_performance: [...moduleMarks.entries()].map(([module, marks]) => ({ module, mark: average(marks) })),
    students: [...students]
      .sort((a, b) => b.risk.risk_score - a.risk.risk_score)
      .slice(0, 10)
      .map((student) => ({
        id: student.student_id,
        name: student.name,
        student_number: student.student_id,
        module: student.modules[0]?.module_name ?? '—',
        average_mark: student.metrics.academic_average,
        attendance: student.metrics.attendance,
        risk_level: student.risk.risk_level,
        ai_explanation: student.risk.evidence.join(' ') || 'No significant negative trend was detected.'
      }))
  };
}
