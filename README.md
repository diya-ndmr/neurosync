# NeuroSync

NeuroSync is a university intelligence platform for identifying students who may need support using attendance, wellbeing, academic performance, study habits, and intervention data.

The project began as a Microsoft Fabric university intelligence platform. This repository also contains the NeuroSync web application: a React/TypeScript frontend, FastAPI backend, SQLAlchemy persistence, CSV workflows, and machine-learning risk analysis.

## Features

- Role-based student, lecturer, advisor, and administrator experiences.
- Student records, attendance, assessments, referrals, interventions, meetings, and follow-ups.
- Topic-level lecturer feedback and assigned learning resources, with student resource progress and explainable recommendations.
- Class-by-class attendance with a rolling 90-day summary; excused and approved-leave sessions are excluded from rates.
- Referral-gated Wellness appointment booking and support-team follow-up management.
- Account-persisted appearance, layout, and study-notification preferences.
- CSV dataset import/export workflows.
- Student risk analysis and intervention recommendations.
- Supabase Auth for production email/password sign-in, email verification, and password recovery.
- Optional local Moodle REST connection check. Moodle remains optional; the connection check does not synchronize course, enrolment, assignment, or grade data.
- Synthetic demo profiles and student risk data for local development.

## Bundled synthetic data pack

The supplied `backend/datasets/NeuroSync_Complete_CSV_Data_Pack.zip` contains 500 students, 36 modules, 110,112 class-attendance records, 8,000 assessments, 1,710 lecturer-feedback rows, 883 learning resources, and 90 historical Wellness bookings. It is imported explicitly rather than replacing application data at startup.

To explicitly import or replace the local demo dataset from the `backend` directory, run:

```powershell
python -m lms.complete_data_pack_import
python -m lms.complete_data_pack_import --replace
```

The complete-pack importer is content-hash idempotent. `--replace` is destructive to existing demo-domain data; do not use it against a populated production database. Production startup does not automatically seed or replace data. The archive's password-hash placeholders are ignored. Imported appointment records do not expose counselling details.

### Separate extended cohort

`backend/datasets/NeuroSync_Extended_Data.zip` is a separate 50-student cohort whose student and assessment identifiers overlap with, but do not identify, the complete-pack students. Import it only as a separate cohort; the importer namespaces its student IDs with `EXT-` and refuses email collisions. Duplicate emails in the source roster are given a `+ext-<student-id>` login suffix so each student account remains unique. The supplied roster creates local student accounts with the configured initial password. For local demo use, set it to `demo1234`:

```powershell
$env:NEUROSYNC_EXTENDED_INITIAL_PASSWORD = 'demo1234'
python -m lms.extended_data_import
Remove-Item Env:NEUROSYNC_EXTENDED_INITIAL_PASSWORD
```

The import connects risk predictions, mood check-ins, study-session durations, recommendations, feedback text, and quiz question outcomes to the new accounts. Phone numbers are not imported. The bundle does not contain module names, assessment titles, assessment dates, or marks for its external assessment IDs, so those fields are not fabricated; quiz correctness is displayed only as recorded and is not treated as mastery. No attendance or Wellness referrals are included, so those sections remain accurately unrecorded and Wellness booking stays referral-gated.

## Technology

- Frontend: React, TypeScript, Vite.
- Backend: Python, FastAPI, SQLAlchemy.
- Local development databases: SQLite.
- Risk analysis: pandas and scikit-learn.
- Optional LMS: Moodle REST Web Services.

## Run locally

Prerequisites: Python 3.11 and Node.js LTS.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`; its OpenAPI docs are at `http://localhost:8000/docs`.

Learning documents are stored in the application database and served only after role and module-enrolment checks. Wellness appointment slots and bookings are managed by NeuroSync; no external university appointment-system connector is configured. Advisors and administrators manage availability and follow-ups, while lecturers cannot view private appointment details.

Study-reminder and weekly-summary selections are persisted as account preferences. This repository does not currently include a notification scheduler or delivery provider.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The login page shows the available development demo profiles. These demo accounts are for local development only.

## Optional Moodle setup

To test a local Moodle connection, configure Moodle Web Services and REST, then create a dedicated integration account and a restricted service. Put `MOODLE_BASE_URL` and the Moodle-generated `MOODLE_TOKEN` in the private `backend/.env` file. The Admin Settings page can test `core_webservice_get_site_info`. See [the Moodle setup guide](backend/lms/moodle-integration.md) for details.

Never commit `.env` files, database passwords, Supabase service-role keys, Moodle tokens, or local database files. A safe environment template is provided at [backend/.env.example](backend/.env.example).

## Supabase-only deployment status

The intended hosting architecture is Supabase Auth, PostgreSQL, and Edge Functions,
with Netlify hosting the frontend. The initial Supabase profile schema, role-based
profile read policy, and administrator account-invitation function are in
[`supabase/`](supabase/README.md). Follow that guide to apply the schema, establish
the first administrator, and deploy invitations.

**The conversion is not yet complete.** Most screens still call the former FastAPI
API, including student data, analytics, attendance, wellbeing, workflow, import,
and prediction features. Those endpoints and their database schema must be
rewritten as Supabase Edge Functions/SQL before the application can operate
without an API server. Do not expect a login alone to make those screens work.
No Render database migration is included; the new Supabase project starts fresh.

The public Supabase anon key may be used by the frontend. Never expose the
service-role key in Netlify variables or browser code.

## Tests and production build

```powershell
cd backend
python -m pytest
```

```powershell
cd frontend
npm run build
```

## Project history

The original Microsoft Fabric project identified at-risk students through a Lakehouse, PySpark notebooks, intelligence tables, a semantic model, dashboards, and an AI agent.

Team: Diya, Vhutali, Sinezipho, Siphiwe, and Zinhle.

Status: Microsoft Fabric Hackathon – 1st Place Winner.


Current Project - Python 
Diya Nandkoomar - Front End 
Siphiwe Sithebe - Back End
Zinhle Dlamini - Business Analysis 
App of the year 2026 - FNB
