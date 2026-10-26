export const DEMO_DATA_NOTICE = 'Demo data only — illustrative examples, not live system state.';

function demoTimestamp(daysAgo: number, hoursAgo = 0): string {
  const timestamp = new Date();
  timestamp.setDate(timestamp.getDate() - daysAgo);
  timestamp.setHours(timestamp.getHours() - hoursAgo);
  return timestamp.toISOString();
}

export const DEMO_INTEGRATION_ACTIVITY = {
  moodle: {
    status: 'Connected',
    site_name: 'Example University Moodle',
    last_sync: demoTimestamp(1, 3),
  },
  imports: [
    {
      event_id: 'demo-import-assessments',
      dataset: 'assessments',
      outcome: 'SUCCESS',
      occurred_at: demoTimestamp(0, 5),
      validation_error: false,
      invalid_rows: 0,
      persisted_rows: 128,
      errors: [],
      errors_truncated: false,
      is_demo: true,
    },
    {
      event_id: 'demo-import-attendance',
      dataset: 'attendance',
      outcome: 'REJECTED',
      occurred_at: demoTimestamp(1, 2),
      validation_error: true,
      invalid_rows: 3,
      persisted_rows: 0,
      errors: [
        { row: 14, field: 'date', code: 'invalid_date', message: 'Date must use ISO format YYYY-MM-DD.' },
        { row: 27, field: 'attendance_percentage', code: 'invalid_number', message: 'Attendance must be a finite number from 0 to 100.' },
      ],
      errors_truncated: false,
      is_demo: true,
    },
    {
      event_id: 'demo-import-students',
      dataset: 'students',
      outcome: 'SUCCESS',
      occurred_at: demoTimestamp(2, 1),
      validation_error: false,
      invalid_rows: 0,
      persisted_rows: 24,
      errors: [],
      errors_truncated: false,
      is_demo: true,
    },
  ],
};

export const DEMO_AUDIT_EVENTS = [
  {
    event_id: 'demo-audit-login',
    actor: 'Alex Morgan (demo)',
    action: 'STAFF_LOGIN',
    outcome: 'SUCCESS',
    occurred_at: demoTimestamp(0, 2),
    is_demo: true,
  },
  {
    event_id: 'demo-audit-permission',
    actor: 'Jordan Lee (demo)',
    action: 'ROLE_PERMISSION_REVIEW',
    outcome: 'SUCCESS',
    occurred_at: demoTimestamp(1, 4),
    is_demo: true,
  },
  {
    event_id: 'demo-audit-import',
    actor: 'Taylor Chen (demo)',
    action: 'CSV_IMPORT_ATTENDANCE',
    outcome: 'REJECTED',
    occurred_at: demoTimestamp(2, 3),
    is_demo: true,
  },
];

export const DEMO_STAFF_SECURITY = [
  { name: 'Alex Morgan (demo)', role: 'Lecturer', mfa: 'Enabled (example)' },
  { name: 'Taylor Chen (demo)', role: 'Advisor', mfa: 'Pending setup (example)' },
  { name: 'Jordan Lee (demo)', role: 'Administrator', mfa: 'Enabled (example)' },
];

export const DEMO_ENCRYPTION_EXAMPLE = [
  { control: 'Transport encryption', status: 'TLS configured (example)' },
  { control: 'Database at-rest encryption', status: 'Provider-managed (example)' },
];
