import type { User, StudentProfile } from '../types';
import { studentDashboard } from './mockData';
import type {
  AttendanceSummary,
  LearningSupportItem,
  LmsAssessmentRow,
  LmsStudySession,
  SupplementaryAssessmentFeedback,
  WellnessReferral,
  WellnessSlot,
  WellbeingCheckin
} from './liveData';

const now = Date.now();
const daysAgo = (days: number) => new Date(now - days * 86400000).toISOString();
const dateOnly = (daysAgoValue: number) => daysAgo(daysAgoValue).slice(0, 10);

export const studentDemoAssessments: LmsAssessmentRow[] = [
  { id: 'demo-assessment-1', module: 'Data Structures', module_code: 'MOD003', module_id: 'MOD003', assessment_type: 'Quiz', title: 'Arrays and linked lists', topic: 'Data structures', mark: 42, max_score: 100, status: 'Graded', assessment_date: dateOnly(25), feedback: 'Review the worked examples before the next quiz.' },
  { id: 'demo-assessment-2', module: 'Data Structures', module_code: 'MOD003', module_id: 'MOD003', assessment_type: 'Assignment', title: 'Core data structures', topic: 'Lists and stacks', mark: 48, max_score: 100, status: 'Graded', assessment_date: dateOnly(12), feedback: 'Good progress; add more detail to the complexity analysis.' },
  { id: 'demo-assessment-3', module: 'Data Structures', module_code: 'MOD003', module_id: 'MOD003', assessment_type: 'Test', title: 'Structures test', topic: 'Trees', mark: 50, max_score: 100, status: 'Graded', assessment_date: dateOnly(4), feedback: 'Revisit tree traversal and practice tracing each step.' },
  { id: 'demo-assessment-4', module: 'Systems Analysis and Design', module_code: 'MOD001', module_id: 'MOD001', assessment_type: 'Assignment', title: 'Requirements analysis', topic: 'Requirements', mark: 38, max_score: 100, status: 'Graded', assessment_date: dateOnly(28), feedback: 'The problem statement is clear; include more supporting user stories.' },
  { id: 'demo-assessment-5', module: 'Systems Analysis and Design', module_code: 'MOD001', module_id: 'MOD001', assessment_type: 'Quiz', title: 'Modelling concepts', topic: 'UML', mark: 42, max_score: 100, status: 'Graded', assessment_date: dateOnly(15), feedback: 'Practice matching UML diagrams to the scenarios.' },
  { id: 'demo-assessment-6', module: 'Systems Analysis and Design', module_code: 'MOD001', module_id: 'MOD001', assessment_type: 'Test', title: 'Systems design test', topic: 'Design methods', mark: 48, max_score: 100, status: 'Graded', assessment_date: dateOnly(3), feedback: 'Review the design-method comparison notes.' },
  { id: 'demo-assessment-7', module: 'Database Systems', module_code: 'MOD002', module_id: 'MOD002', assessment_type: 'Quiz', title: 'Relational modelling', topic: 'Relational databases', mark: 60, max_score: 100, status: 'Graded', assessment_date: dateOnly(24), feedback: 'Good grasp of keys; revisit relationship cardinality.' },
  { id: 'demo-assessment-8', module: 'Database Systems', module_code: 'MOD002', module_id: 'MOD002', assessment_type: 'Assignment', title: 'Database design', topic: 'Normalisation', mark: 62, max_score: 100, status: 'Graded', assessment_date: dateOnly(10), feedback: 'Check the normal forms and document your assumptions.' },
  { id: 'demo-assessment-9', module: 'Database Systems', module_code: 'MOD002', module_id: 'MOD002', assessment_type: 'Test', title: 'SQL fundamentals', topic: 'SQL', mark: 65, max_score: 100, status: 'Graded', assessment_date: dateOnly(2), feedback: 'Strong queries; continue practicing joins.' },
  { id: 'demo-assessment-10', module: 'IT Project Management', module_code: 'MOD004', module_id: 'MOD004', assessment_type: 'Quiz', title: 'Planning fundamentals', topic: 'Project planning', mark: 56, max_score: 100, status: 'Graded', assessment_date: dateOnly(27), feedback: 'Review dependencies and milestone sequencing.' },
  { id: 'demo-assessment-11', module: 'IT Project Management', module_code: 'MOD004', module_id: 'MOD004', assessment_type: 'Assignment', title: 'Project schedule', topic: 'Scheduling', mark: 58, max_score: 100, status: 'Graded', assessment_date: dateOnly(13), feedback: 'The plan is clear; add a short risk response for each major risk.' },
  { id: 'demo-assessment-12', module: 'IT Project Management', module_code: 'MOD004', module_id: 'MOD004', assessment_type: 'Test', title: 'Project delivery test', topic: 'Delivery', mark: 62, max_score: 100, status: 'Graded', assessment_date: dateOnly(1), feedback: 'Review change control and stakeholder communication.' }
];

const attendanceStart = (daysAgoValue: number) => new Date(now - daysAgoValue * 86400000);
const attendanceMonth = (label: string, startDaysAgo: number, endDaysAgo: number, classes: number) => {
  const periodStart = attendanceStart(startDaysAgo);
  const periodEnd = attendanceStart(endDaysAgo);
  const attended = Math.round(classes * 0.8);
  return {
    month: label,
    period_start: periodStart.toISOString().slice(0, 10),
    period_end: periodEnd.toISOString().slice(0, 10),
    percentage: 80,
    attended,
    classes
  };
};

const attendancePeriods = [
  attendanceMonth('Month 1', 90, 61, 10),
  attendanceMonth('Month 2', 60, 31, 10),
  attendanceMonth('Month 3', 30, 0, 20)
];
const attendanceModules = ['Data Structures', 'Database Systems', 'IT Project Management', 'Systems Analysis and Design'];
const demoAttendanceRecords = Array.from({ length: 40 }, (_, index) => {
  const daysOffset = 89 - Math.floor(index * 89 / 39);
  return {
    id: `demo-attendance-${index + 1}`,
    module: attendanceModules[index % attendanceModules.length],
    module_code: ['MOD003', 'MOD002', 'MOD004', 'MOD001'][index % attendanceModules.length],
    class_name: index % 2 === 0 ? 'Lecture' : 'Tutorial',
    date: dateOnly(daysOffset),
    status: index % 5 === 4 ? 'absent' : 'present'
  };
});

const attendedCount = demoAttendanceRecords.filter((record) => record.status === 'present').length;

export const studentDemoAttendance: AttendanceSummary = {
  period_start: attendancePeriods[0].period_start,
  period_end: attendancePeriods[2].period_end,
  attendance_rate: Math.round(attendedCount / demoAttendanceRecords.length * 100),
  classes_attended: attendedCount,
  classes_counted: demoAttendanceRecords.length,
  excused_absences: 0,
  monthly_breakdown: attendancePeriods,
  records: demoAttendanceRecords
};

export const studentDemoStudySessions: LmsStudySession[] = [
  { id: 'demo-study-1', subject: 'Data Structures', duration_minutes: 50, activity_type: 'revision', created_at: daysAgo(1) },
  { id: 'demo-study-2', subject: 'Database Systems', duration_minutes: 40, activity_type: 'practice', created_at: daysAgo(2) },
  { id: 'demo-study-3', subject: 'Systems Analysis and Design', duration_minutes: 35, activity_type: 'reading', created_at: daysAgo(3) },
  { id: 'demo-study-4', subject: 'IT Project Management', duration_minutes: 60, activity_type: 'assignment', created_at: daysAgo(5) }
];

export const studentDemoFeedback: SupplementaryAssessmentFeedback[] = [
  { assessment_id: 'DEMO-QUIZ-01', feedback: 'Review the questions you missed and revisit the related lecture notes.', questions: [{ question_id: 'Q1', is_correct: true }, { question_id: 'Q2', is_correct: false }, { question_id: 'Q3', is_correct: true }], correct_count: 2, question_count: 3 },
  { assessment_id: 'DEMO-QUIZ-02', feedback: 'Good work. Practice a few more examples to reinforce the topic.', questions: [{ question_id: 'Q1', is_correct: true }, { question_id: 'Q2', is_correct: true }], correct_count: 2, question_count: 2 }
];

export const studentDemoWellbeing: WellbeingCheckin[] = [
  { id: 'demo-wellbeing-1', mood_score: 7, stress_level: 4, notes: 'Demo check-in: feeling focused this week.', created_at: daysAgo(1) },
  { id: 'demo-wellbeing-2', mood_score: 6, stress_level: 6, notes: 'Demo check-in: balancing coursework and revision.', created_at: daysAgo(4) },
  { id: 'demo-wellbeing-3', mood_score: 8, stress_level: 3, notes: 'Demo check-in: feeling positive after completing a task.', created_at: daysAgo(8) },
  { id: 'demo-wellbeing-4', mood_score: 6, stress_level: 5, notes: 'Demo check-in: planning study time for the week.', created_at: daysAgo(12) }
];

export const studentDemoLearningSupport: LearningSupportItem[] = [
  {
    feedback_id: 'DEMO-FEEDBACK-DS',
    topic_id: 'DEMO-TOPIC-DS',
    module: 'Data Structures',
    topic: 'Trees and traversal',
    strengths: ['Understands core data structure terminology'],
    learning_gaps: ['Tree traversal practice', 'Explaining time complexity'],
    feedback: 'Work through a small tree example and write out the traversal order at each step.',
    learning_goal: 'Complete two tree traversal practice problems.',
    goal_due_date: dateOnly(-7),
    recommendation_explanation: 'Illustrative support suggestion based on sample assessment feedback.',
    performance_context: { module_average: 46.7, explanation: 'Sample module average shown for demonstration only.' },
    resources: []
  },
  {
    feedback_id: 'DEMO-FEEDBACK-DB',
    topic_id: 'DEMO-TOPIC-DB',
    module: 'Database Systems',
    topic: 'Normalisation and joins',
    strengths: ['Writes basic SQL queries'],
    learning_gaps: ['Checking normal forms', 'Practicing multi-table joins'],
    feedback: 'Review the normalisation steps and test joins with a small example dataset.',
    learning_goal: 'Review one normalisation example and write three practice joins.',
    goal_due_date: dateOnly(-10),
    recommendation_explanation: 'Illustrative support suggestion based on sample assessment feedback.',
    performance_context: { module_average: 62.3, explanation: 'Sample module average shown for demonstration only.' },
    resources: []
  }
];

export const studentDemoWellnessReferrals: WellnessReferral[] = [
  { id: 'DEMO-WELLNESS-REFERRAL', status: 'active', student_message: 'Demo support example: wellness support is available if you would like to speak with the team.', created_at: daysAgo(2) }
];

export const studentDemoWellnessSlots: WellnessSlot[] = [
  { id: 'DEMO-WELLNESS-SLOT-1', starts_at: daysAgo(-2), duration_minutes: 30, location: 'Student Wellness Centre (demo)' },
  { id: 'DEMO-WELLNESS-SLOT-2', starts_at: daysAgo(-4), duration_minutes: 45, location: 'Online appointment (demo)' }
];

export const studentDemoAppointments = [
  { id: 'DEMO-APPOINTMENT', status: 'scheduled', starts_at: daysAgo(-6), location: 'Student Wellness Centre (demo)' }
];

export function createStudentDemoProfile(user: User | null): StudentProfile {
  const name = user?.name || 'Demo Student';
  const [firstName, ...surnameParts] = name.trim().split(/\s+/);
  return {
    ...studentDashboard.student,
    id: 'DEMO-STUDENT',
    user_id: user?.id || 'DEMO-USER',
    student_number: 'DEMO-STU-001',
    first_name: firstName || 'Demo',
    surname: surnameParts.join(' ') || 'Student',
    created_at: daysAgo(180)
  };
}

export function createStudentDemoDashboard(user: User | null) {
  return {
    ...studentDashboard,
    student: createStudentDemoProfile(user),
    performance: {
      ...studentDashboard.performance,
      module_breakdown: studentDemoAssessments.reduce<{ module: string; mark: number }[]>((modules, assessment) => {
        const module = modules.find((item) => item.module === assessment.module);
        if (module) {
          const related = studentDemoAssessments.filter((item) => item.module === assessment.module);
          module.mark = Math.round(related.reduce((total, item) => total + item.mark, 0) / related.length);
        } else {
          modules.push({ module: assessment.module, mark: assessment.mark });
        }
        return modules;
      }, [])
    }
  };
}
