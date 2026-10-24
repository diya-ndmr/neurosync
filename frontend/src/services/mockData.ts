import type {
  AdminAnalytics,
  AdvisorDashboardData,
  LecturerDashboardData,
  StudentDashboardData,
  User
} from '../types';

const now = new Date().toISOString();
const daysAgo = (d: number) => new Date(Date.now() - d * 86400000).toISOString();

export const demoUsers: User[] = [
  { id: 'u-sarah', name: 'Sarah Johnson', email: 'sarah@university.edu', role: 'student' },
  { id: 'u-lecturer', name: 'Dr. Mark Thompson', email: 'lecturer@university.edu', role: 'lecturer' },
  { id: 'u-advisor', name: 'Amelia Richards', email: 'advisor@university.edu', role: 'advisor' },
  { id: 'u-admin', name: 'Prof. James Carter', email: 'admin@university.edu', role: 'admin' }
];

export const studentDashboard: StudentDashboardData = {
  student: {
    id: 's-1001',
    user_id: 'u-sarah',
    student_number: 'NS2024001',
    first_name: 'Sarah',
    surname: 'Johnson',
    programme: 'Bachelor of Information Technology',
    year_level: 2,
    created_at: now
  },
  performance: {
    current_average: 78,
    trend: 'improving',
    history: [
      { month: 'Mar', average: 71 },
      { month: 'Apr', average: 73 },
      { month: 'May', average: 76 },
      { month: 'Jun', average: 74 },
      { month: 'Jul', average: 78 },
      { month: 'Aug', average: 78 }
    ],
    module_breakdown: [
      { module: 'Database Systems', mark: 82 },
      { module: 'Web Development', mark: 76 },
      { module: 'Data Structures', mark: 71 },
      { module: 'Networking', mark: 84 },
      { module: 'Software Engineering', mark: 77 }
    ]
  },
  attendance: {
    current: 85,
    previous: 95,
    change: -10,
    status: 'Good',
    history: [
      { month: 'Mar', percentage: 96 },
      { month: 'Apr', percentage: 93 },
      { month: 'May', percentage: 90 },
      { month: 'Jun', percentage: 87 },
      { month: 'Jul', percentage: 86 },
      { month: 'Aug', percentage: 85 }
    ]
  },
  risk: {
    id: 'r-1',
    risk_score: 62,
    risk_level: 'MEDIUM',
    explanation:
      'Your risk increased because attendance dropped by 10%, assignment marks decreased in one module, and study activity reduced.',
    factors: [
      { factor: 'Attendance dropped by 10%', impact: 'High', direction: 'increase' },
      { factor: 'Data Structures assignment marks decreased', impact: 'Medium', direction: 'increase' },
      { factor: 'Weekly study sessions reduced by 2 hours', impact: 'Medium', direction: 'increase' },
      { factor: 'Recent mood check-ins improved', impact: 'Low', direction: 'decrease' }
    ],
    model_version: 'gradient_boost_v1.0',
    created_at: now
  },
  recommendations: [
    {
      id: 'rec-1',
      category: 'attendance',
      message: 'Attend additional Database Systems tutorials to strengthen practical skills.',
      priority: 'high',
      status: 'new',
      created_at: now
    },
    {
      id: 'rec-2',
      category: 'study',
      message: 'Increase weekly study sessions by 2 hours to cover Data Structures topics.',
      priority: 'medium',
      status: 'new',
      created_at: now
    },
    {
      id: 'rec-3',
      category: 'wellbeing',
      message: 'Book a session with the student wellbeing service to manage stress.',
      priority: 'low',
      status: 'completed',
      created_at: daysAgo(6)
    },
    {
      id: 'rec-4',
      category: 'academic',
      message: 'Attend the academic support workshop for algorithms and complexity.',
      priority: 'medium',
      status: 'completed',
      created_at: daysAgo(12)
    }
  ],
  wellbeing: {
    mood_score: 7,
    stress_level: 6,
    last_checkin: daysAgo(2)
  }
};

const studentRows = [
  {
    id: 's-2001',
    name: 'Sarah Johnson',
    student_number: 'NS2024001',
    module: 'Data Structures',
    average_mark: 71,
    attendance: 85,
    risk_level: 'MEDIUM' as const,
    ai_explanation: 'Attendance declined 10%; assignment marks trending down.'
  },
  {
    id: 's-2002',
    name: 'Liam Patel',
    student_number: 'NS2024022',
    module: 'Database Systems',
    average_mark: 54,
    attendance: 62,
    risk_level: 'HIGH' as const,
    ai_explanation: 'Attendance below 70%, average mark below 60%, multiple missed deadlines.'
  },
  {
    id: 's-2003',
    name: 'Aisha Mohammed',
    student_number: 'NS2024034',
    module: 'Web Development',
    average_mark: 88,
    attendance: 97,
    risk_level: 'LOW' as const,
    ai_explanation: 'Consistent attendance and strong assessment performance.'
  },
  {
    id: 's-2004',
    name: 'Daniel Osei',
    student_number: 'NS2024051',
    module: 'Networking',
    average_mark: 63,
    attendance: 78,
    risk_level: 'MEDIUM' as const,
    ai_explanation: 'Recent quiz scores dropped while study activity reduced.'
  },
  {
    id: 's-2005',
    name: 'Emma Botha',
    student_number: 'NS2024067',
    module: 'Software Engineering',
    average_mark: 81,
    attendance: 90,
    risk_level: 'LOW' as const,
    ai_explanation: 'Stable academic performance with high engagement.'
  },
  {
    id: 's-2006',
    name: 'Noah van der Berg',
    student_number: 'NS2024090',
    module: 'Data Structures',
    average_mark: 48,
    attendance: 55,
    risk_level: 'HIGH' as const,
    ai_explanation: 'Attendance critically low, failed last assessment, low wellbeing scores.'
  }
];

export const lecturerDashboard: LecturerDashboardData = {
  total_students: 128,
  average_mark: 72,
  average_attendance: 86,
  students_at_risk: 14,
  class_performance: [
    { month: 'Mar', average: 68 },
    { month: 'Apr', average: 70 },
    { month: 'May', average: 69 },
    { month: 'Jun', average: 73 },
    { month: 'Jul', average: 71 },
    { month: 'Aug', average: 72 }
  ],
  module_performance: [
    { module: 'Database Systems', mark: 76 },
    { module: 'Web Development', mark: 81 },
    { module: 'Data Structures', mark: 64 },
    { module: 'Networking', mark: 78 },
    { module: 'Software Engineering', mark: 72 }
  ],
  risk_distribution: [
    { name: 'LOW', value: 72 },
    { name: 'MEDIUM', value: 42 },
    { name: 'HIGH', value: 14 }
  ],
  students: studentRows
};

export const advisorDashboard: AdvisorDashboardData = {
  open_cases: 12,
  resolved_cases: 34,
  high_priority_cases: 5,
  cases: [
    {
      id: 'c-1',
      student_name: 'Liam Patel',
      student_number: 'NS2024022',
      risk_level: 'HIGH',
      issue: 'Chronic attendance issues and failing Data Structures',
      action_required: 'Schedule 1-on-1 and academic support plan',
      status: 'open',
      priority: 'high'
    },
    {
      id: 'c-2',
      student_name: 'Sarah Johnson',
      student_number: 'NS2024001',
      risk_level: 'MEDIUM',
      issue: 'Declining attendance and reduced study activity',
      action_required: 'Review study habits and recommend tutor',
      status: 'in_progress',
      priority: 'medium'
    },
    {
      id: 'c-3',
      student_name: 'Noah van der Berg',
      student_number: 'NS2024090',
      risk_level: 'HIGH',
      issue: 'Failing assessments and low wellbeing scores',
      action_required: 'Immediate wellbeing referral and catch-up plan',
      status: 'open',
      priority: 'high'
    },
    {
      id: 'c-4',
      student_name: 'Daniel Osei',
      student_number: 'NS2024051',
      risk_level: 'MEDIUM',
      issue: 'Recent quiz score decline',
      action_required: 'Monitor next assessment cycle',
      status: 'open',
      priority: 'medium'
    },
    {
      id: 'c-5',
      student_name: 'Chloe Adams',
      student_number: 'NS2024075',
      risk_level: 'LOW',
      issue: 'Brief wellbeing dip after exam period',
      action_required: 'Follow-up check-in next month',
      status: 'resolved',
      priority: 'low'
    }
  ]
};

export const adminAnalytics: AdminAnalytics = {
  total_students: 5240,
  active_students: 4918,
  average_performance: 72,
  retention_rate: 91,
  high_risk_students: 318,
  risk_distribution: [
    { name: 'LOW', value: 3421 },
    { name: 'MEDIUM', value: 1501 },
    { name: 'HIGH', value: 318 }
  ],
  attendance_trend: [
    { month: 'Mar', percentage: 88 },
    { month: 'Apr', percentage: 87 },
    { month: 'May', percentage: 86 },
    { month: 'Jun', percentage: 87 },
    { month: 'Jul', percentage: 85 },
    { month: 'Aug', percentage: 86 }
  ],
  performance_trend: [
    { month: 'Mar', average: 69 },
    { month: 'Apr', average: 71 },
    { month: 'May', average: 70 },
    { month: 'Jun', average: 72 },
    { month: 'Jul', average: 73 },
    { month: 'Aug', average: 72 }
  ],
  programme_comparison: [
    { programme: 'Computer Science', average: 74, students: 1240 },
    { programme: 'Information Technology', average: 71, students: 980 },
    { programme: 'Software Engineering', average: 76, students: 860 },
    { programme: 'Data Science', average: 78, students: 720 },
    { programme: 'Cybersecurity', average: 69, students: 640 },
    { programme: 'Information Systems', average: 70, students: 800 }
  ]
};

