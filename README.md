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

## Deploying the backend to Render, database and auth to Supabase, and frontend to Netlify

### 1. Create Supabase project

Create a Supabase project and save its project URL, public anon/publishable API key, and database password. In **Authentication → Providers**, enable Email and Password and leave email confirmation enabled. The backend checks the confirmed address with Supabase before creating a NeuroSync session.

For database access, use the connection string shown by the Supabase dashboard's **Connect** button. Render is a persistent backend; use the direct connection if the Render region/network supports its IP version, or the Supabase **Session pooler** connection otherwise. Do not use the transaction pooler for this SQLAlchemy application. Replace the password placeholder and URL-encode special characters in the password. The application and mock LMS tables use the same Supabase database but are kept in separate schemas (`public` and `mock_lms`); the backend creates the `mock_lms` schema at startup.

**Email delivery limitation:** Supabase's default Auth SMTP is for testing only. It only sends to project team members and is currently limited to about two messages per hour. To allow sign-up and password recovery for real users, configure a custom SMTP provider in **Authentication → SMTP Settings**. A provider may require a verified sender domain. Without custom SMTP, test only with an authorized team email. See [Supabase custom SMTP guidance](https://supabase.com/docs/guides/auth/auth-smtp).

### 2. Deploy the FastAPI backend to Render

The root [render.yaml](render.yaml) defines the backend only. In Render, use **New + → Blueprint**, connect this GitHub repository, select `main`, review the `neurosync-backend` service, and apply it. The Blueprint prompts for values marked `sync: false`; alternatively add them later under **neurosync-backend → Environment**:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Supabase PostgreSQL connection string from **Connect** |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase public anon/publishable key (never the service-role/secret key) |
| `FRONTEND_URL` | Netlify production origin, e.g. `https://your-site.netlify.app` |
| `CORS_ORIGINS` | JSON array of allowed frontend origins, e.g. `["https://your-site.netlify.app"]` |

The Blueprint also sets `ENVIRONMENT=production`, creates a strong `SECRET_KEY`, disables demo tokens and mock SSO, and pins Python to 3.11.9. Keep those settings. The backend URL shown in Render is needed for Netlify's `VITE_API_URL`.

### 3. Deploy the frontend from GitHub to Netlify

In Netlify, choose **Add new site → Import an existing project**, connect GitHub, select this repository, and deploy the `main` branch. The committed [netlify.toml](netlify.toml) configures the frontend build and single-page-app routes. Add these under **Site configuration → Environment variables** (or **Site settings → Environment variables**) for the Production context:

| Variable | Value |
| --- | --- |
| `VITE_API_URL` | Render backend base URL, without `/api` |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase public anon/publishable key |

Trigger a new Netlify deploy after adding variables because Vite embeds them during build. The public anon key is intended for frontend use; never use or expose the Supabase service-role key.

### 4. Configure Auth redirect URLs and test

In Supabase **Authentication → URL Configuration**, set **Site URL** to the Netlify production URL and add that exact URL plus `/login` and `/reset-password` as allowed redirect destinations (e.g. `https://your-site.netlify.app/**`). If you use a custom Netlify domain, use it consistently in these settings, Render's `FRONTEND_URL`/`CORS_ORIGINS`, and the browser.

### 5. Migrate existing Render database data before cutover

If the existing Render databases contain data, keep both databases running until the Supabase copy has been checked. Get each database's **external** PostgreSQL connection URL from its Render database page. Run the migration once, from a local PowerShell terminal, before any users sign up. It is okay if the backend has already created empty tables in Supabase:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:SOURCE_APP_DATABASE_URL = [System.Net.NetworkCredential]::new("", (Read-Host "Render app database URL" -AsSecureString)).Password
$env:SOURCE_LMS_DATABASE_URL = [System.Net.NetworkCredential]::new("", (Read-Host "Render LMS database URL" -AsSecureString)).Password
$env:SUPABASE_DATABASE_URL = [System.Net.NetworkCredential]::new("", (Read-Host "Supabase PostgreSQL URL" -AsSecureString)).Password
python migrate_render_to_supabase.py
Remove-Item Env:SOURCE_APP_DATABASE_URL, Env:SOURCE_LMS_DATABASE_URL, Env:SUPABASE_DATABASE_URL
```

Use the database connection URLs, not the Supabase project URL or API key. The script copies application tables into Supabase `public` and LMS tables into `mock_lms`, retaining foreign-key relationships. It reports table counts only, and it stops on conflicting rows rather than overwriting them. If the migration fails, keep the Render databases; inspect the error and do not delete either source. Verify the app and LMS data in the deployed site before manually deleting old Render databases. Previous email-provider credentials/passwords are not migrated; users create a new Supabase Auth account with the same verified email to retain their NeuroSync app role/data association.

After both deploys finish, check `https://YOUR-RENDER-BACKEND/api/ready`. Register an account using an email address that can receive mail, click the confirmation link, then sign in and test password recovery. Public sign-up creates student accounts. For staff, an administrator reserves the email and role in NeuroSync first; the staff member signs up with that exact verified address.

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

Team: Diya Nandkoomar, Vhutali, Sinezipho, Siphiwe, and Zinhle.

Status: Microsoft Fabric Hackathon – 1st Place Winner.
