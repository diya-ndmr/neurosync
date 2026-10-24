# NeuroSync

NeuroSync is a university intelligence platform for identifying students who may need support using attendance, wellbeing, academic performance, study habits, and intervention data.

The project began as a Microsoft Fabric university intelligence platform. This repository also contains the NeuroSync web application: a React/TypeScript frontend, FastAPI backend, SQLAlchemy persistence, CSV workflows, and machine-learning risk analysis.

## Features

- Role-based student, lecturer, advisor, and administrator experiences.
- Student records, attendance, assessments, referrals, interventions, meetings, and follow-ups.
- CSV dataset import/export workflows.
- Student risk analysis and intervention recommendations.
- Optional local Moodle REST connection check. Moodle remains optional; the connection check does not synchronize course, enrolment, assignment, or grade data.
- Synthetic demo profiles and student risk data for local development.

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

Never commit `.env` files, Moodle tokens, email API keys, or local database files. A safe environment template is provided at [backend/.env.example](backend/.env.example).

## Tests and production build

```powershell
cd backend
python -m pytest tests
```

```powershell
cd frontend
npm run build
```

## Project history

The original Microsoft Fabric project identified at-risk students through a Lakehouse, PySpark notebooks, intelligence tables, a semantic model, dashboards, and an AI agent.

Team: Diya Nandkoomar, Vhutali, Sinezipho, Siphiwe, and Zinhle.

Status: Microsoft Fabric Hackathon – 1st Place Winner.
