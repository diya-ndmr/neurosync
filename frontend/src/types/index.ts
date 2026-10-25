export type Role = 'student' | 'lecturer' | 'advisor' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar?: string;
}

export interface StudentProfile {
  id: string;
  user_id: string;
  student_number: string;
  first_name: string;
  surname: string;
  programme: string;
  year_level: number;
  created_at: string;
}

export interface Assessment {
  id: string;
  module: string;
  module_code: string;
  assessment_type: string;
  mark: number;
  assessment_date: string;
}

export interface AttendanceRecord {
  id: string;
  module: string;
  module_code: string;
  attendance_percentage: number;
  date: string;
}

export interface MoodCheckin {
  id: string;
  mood_score: number;
  stress_level: number;
  notes?: string;
  created_at: string;
}

export interface RiskPrediction {
  id?: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  explanation: string;
  factors: RiskFactor[];
  model_version: string;
  created_at: string;
}

export interface RiskFactor {
  factor: string;
  impact: string;
  direction: 'increase' | 'decrease';
}

export interface Recommendation {
  id: string;
  category: 'academic' | 'attendance' | 'wellbeing' | 'study' | 'administrative';
  message: string;
  priority: 'high' | 'medium' | 'low';
  status: 'new' | 'completed' | 'in_progress';
  created_at: string;
}

export interface PerformancePoint {
  month: string;
  average: number;
}

export interface StudentDashboardData {
  student: StudentProfile;
  performance: {
    current_average: number | null;
    trend: 'improving' | 'declining' | 'stable';
    history: PerformancePoint[];
    module_breakdown: { module: string; mark: number }[];
  };
  attendance: {
    current: number | null;
    previous: number | null;
    change: number | null;
    status: 'Good' | 'Warning' | 'At Risk' | 'Not recorded';
    history: { month: string; percentage: number }[];
  };
  risk: RiskPrediction;
  recommendations: Recommendation[];
  wellbeing: {
    mood_score: number | null;
    stress_level: number | null;
    last_checkin: string;
  };
}

export interface StudentRow {
  id: string;
  name: string;
  student_number: string;
  module: string;
  average_mark: number;
  attendance: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  ai_explanation: string;
}

export interface LecturerDashboardData {
  total_students: number;
  average_mark: number;
  average_attendance: number;
  students_at_risk: number;
  class_performance: PerformancePoint[];
  module_performance: { module: string; mark: number }[];
  risk_distribution: { name: string; value: number }[];
  students: StudentRow[];
}

export interface AdvisorCase {
  id: string;
  student_name: string;
  student_number: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  issue: string;
  action_required: string;
  status: 'open' | 'in_progress' | 'resolved';
  priority: 'high' | 'medium' | 'low';
}

export interface AdvisorDashboardData {
  open_cases: number;
  resolved_cases: number;
  high_priority_cases: number;
  cases: AdvisorCase[];
}

export interface LmsStudentSummary {
  student_id: string;
  name: string;
  programme: string;
  year_of_study: number;
  institutional_email: string;
  enrolment_status: string;
  modules: { module_id: string; module_code: string; module_name: string }[];
  metrics: {
    academic_average: number;
    attendance: number;
    attendance_30d: number;
    attendance_7d: number;
    attendance_change_30d: number;
    submission_rate: number;
    late_submissions: number;
    missing_submissions: number;
    quiz_average: number;
    quiz_completion_rate: number;
    engagement_score: number;
    assessment_trend: 'improving' | 'declining' | 'stable';
  };
  risk: {
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    risk_score: number;
    evidence: string[];
    trajectory: 'improving' | 'stable' | 'slowly_deteriorating' | 'rapidly_deteriorating';
    trajectory_evidence: string[];
  };
}

export interface LmsStudentReview {
  student: {
    student_id: string;
    name: string;
    programme: string;
    faculty: string;
    year_of_study: number;
    institutional_email: string;
    enrolment_status: string;
  };
  modules: { module_id: string; module_code: string; module_name: string }[];
  metrics: LmsStudentSummary['metrics'] & {
    classes_attended: number;
    classes_missed: number;
    late_arrivals: number;
    last_login: string | null;
    days_since_last_login: number | null;
    logins_this_week: number;
    resources_viewed: number;
    resources_downloaded: number;
    assessment_pages_viewed: number;
    quiz_activity: number;
    discussion_activity: number;
  };
  risk: {
    risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
    risk_score: number;
    evidence: string[];
    trajectory: 'improving' | 'stable' | 'slowly_deteriorating' | 'rapidly_deteriorating';
    trajectory_evidence: string[];
  };
  attendance: { date: string; session: string; module_id: string; status: string }[];
  submissions: {
    submission_id: string; assessment_id: string; assessment: string; module_id: string; module_code: string;
    type: string; due_date: string; submitted_at: string | null; status: string; mark: number | null; weight: number;
    feedback: string | null;
  }[];
  assessments: {
    assessment_id: string; assessment: string; type: string; module_id: string; module_code: string;
    due_date: string; weight: number; mark: number; status: string;
  }[];
  quizzes: {
    quiz: string; module_code: string; attempt: number; score: number; percentage: number;
    completed_at: string | null; duration: number;
  }[];
  referrals: LmsReferral[];
  interventions: LmsIntervention[];
  timeline: { event_type: string; summary: string; occurred_at: string }[];
  intervention_comparison: LmsInterventionComparison | null;
}

export interface LmsInterventionComparison {
  referral_id: string;
  student_id: string;
  baseline_captured_at: string;
  baseline_risk_level: string;
  baseline_risk_score: number;
  current_risk_level: string;
  current_risk_score: number;
  has_recorded_intervention: boolean;
  intervention_count: number;
  direction: 'IMPROVED' | 'DECLINED' | 'UNCHANGED' | 'MIXED';
  summary: string;
  caveat: string;
  changes: {
    metric: string;
    label: string;
    unit: string;
    before: number;
    current: number;
    change: number;
    direction: 'IMPROVED' | 'DECLINED' | 'UNCHANGED';
  }[];
}

export interface LmsReferral {
  referral_id: string;
  student_id: string;
  student_name?: string;
  lecturer_id: string;
  advisor_user_id: string | null;
  module_id: string | null;
  risk_level: string;
  risk_score: number;
  reason: string;
  lecturer_notes: string | null;
  urgency: 'STANDARD' | 'PRIORITY';
  status: string;
  created_at: string;
}

export interface LmsIntervention {
  intervention_id: string;
  referral_id: string;
  strategy: string;
  reason: string;
  status: string;
  date_started: string;
  review_date: string | null;
  follow_up_date: string | null;
  outcome: string | null;
}

export interface AdminAnalytics {
  total_students: number;
  active_students: number | null;
  average_performance: number | null;
  retention_rate: number | null;
  high_risk_students: number;
  risk_distribution: { name: string; value: number }[];
  attendance_trend: { month: string; percentage: number }[];
  performance_trend: { month: string; average: number }[];
  programme_comparison: { programme: string; average: number; students: number }[];
}
