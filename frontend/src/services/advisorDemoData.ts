import { lecturerDashboard } from './mockData';
import type { LmsIntervention, LmsReferral } from '../types';

const today = new Date();
const dateOffset = (days: number) => new Date(today.getTime() + days * 86400000).toISOString();
const dateOnlyOffset = (days: number) => dateOffset(days).slice(0, 10);

export const advisorDemoReferrals: LmsReferral[] = lecturerDashboard.students.map((student, index) => ({
  referral_id: `DEMO-REF-${student.student_number}`,
  student_id: student.student_number,
  student_name: student.name,
  lecturer_id: 'DEMO-LECTURER',
  advisor_user_id: 'DEMO-ADVISOR',
  module_id: student.module,
  risk_level: student.risk_level,
  risk_score: student.risk_level === 'HIGH' ? 80 : student.risk_level === 'MEDIUM' ? 55 : 20,
  reason: student.ai_explanation,
  lecturer_notes: null,
  urgency: student.risk_level === 'HIGH' ? 'PRIORITY' : 'STANDARD',
  status: index === 0 ? 'ASSIGNED' : index === 1 ? 'IN_REVIEW' : index === 3 ? 'RESOLVED' : 'REFERRED',
  created_at: dateOffset(-index)
}));

export const advisorDemoSummary = {
  new_referrals: advisorDemoReferrals.filter((item) => item.status === 'REFERRED').length,
  assigned_students: advisorDemoReferrals.filter((item) => item.status === 'ASSIGNED').length,
  students_to_contact: advisorDemoReferrals.filter((item) => item.status === 'IN_REVIEW').length,
  awaiting_response: 0,
  meetings_scheduled: 0,
  active_interventions: 2,
  follow_ups_due: 1,
  resolved_cases: advisorDemoReferrals.filter((item) => item.status === 'RESOLVED').length
};

export const advisorDemoInterventions: (LmsIntervention & {
  student_id: string;
  student_name: string;
  referral_status: string;
})[] = advisorDemoReferrals
  .filter((referral) => referral.risk_level !== 'LOW')
  .slice(0, 3)
  .map((referral, index) => ({
    intervention_id: `DEMO-INT-${index + 1}`,
    referral_id: referral.referral_id,
    strategy: index === 0 ? 'Attendance support check-in' : 'Academic planning session',
    reason: referral.reason,
    status: index === 2 ? 'COMPLETED' : index === 1 ? 'FOLLOW_UP' : 'ACTIVE',
    date_started: dateOffset(-(index + 3)),
    review_date: dateOnlyOffset(index === 1 ? 2 : 7),
    follow_up_date: dateOnlyOffset(index === 1 ? -1 : 5),
    outcome: index === 2 ? 'Demo record marked stable after review.' : null,
    student_id: referral.student_id,
    student_name: referral.student_name ?? referral.student_id,
    referral_status: referral.status
  }));

export function advisorDemoReferral(referralId: string): LmsReferral | undefined {
  return advisorDemoReferrals.find((referral) => referral.referral_id === referralId);
}

export const advisorDemoBriefing = {
  role: 'advisor',
  period_days: 7,
  summary: {
    demo_referrals: advisorDemoReferrals.length,
    high_risk: advisorDemoReferrals.filter((item) => item.risk_level === 'HIGH').length,
    active_demo_interventions: advisorDemoInterventions.filter((item) => item.status !== 'COMPLETED').length
  },
  items: advisorDemoReferrals.slice(0, 5).map((referral) => ({
    type: referral.status === 'RESOLVED' ? 'case_resolved' : 'referral_review',
    referral_id: referral.referral_id,
    student_id: referral.student_id,
    risk_level: referral.risk_level,
    urgency: referral.urgency,
    status: referral.status,
    recorded_at: referral.created_at
  })),
  data_basis: 'Illustrative demo records shared with the Lecturer view. These are not live backend records.'
};

export const advisorDemoSupportRequests = advisorDemoReferrals.slice(0, 2).map((referral, index) => ({
  id: `DEMO-SUPPORT-${index + 1}`,
  student_id: referral.student_id,
  student_name: referral.student_name ?? referral.student_id,
  request_type: index === 0 ? 'Academic support' : 'Attendance check-in',
  message: 'Illustrative student request for an advisor check-in.',
  status: 'OPEN' as const,
  created_at: referral.created_at
}));

export const advisorDemoWellnessData = {
  appointments: [{
    id: 'DEMO-APPOINTMENT-1',
    student_id: advisorDemoReferrals[0].student_id,
    status: 'scheduled',
    starts_at: dateOffset(2),
    duration_minutes: 30,
    location: 'Advisor meeting room',
    follow_up: null
  }],
  slots: [{
    id: 'DEMO-SLOT-1',
    starts_at: dateOffset(3),
    duration_minutes: 30,
    location: 'Advisor meeting room',
    active: true,
    booked: false
  }],
  referrals: [{
    id: 'DEMO-WELLNESS-1',
    student_id: advisorDemoReferrals[1].student_id,
    student_name: advisorDemoReferrals[1].student_name ?? advisorDemoReferrals[1].student_id,
    status: 'active',
    created_at: advisorDemoReferrals[1].created_at
  }]
};
