"""
NeuroSync Backend — FastAPI Application
AI University Intelligence Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.database.connection import engine, Base
from app.api import (
    auth,
    admin_users,
    csv_data,
    health,
    students,
    assessments,
    attendance,
    wellbeing,
    predictions,
    analytics,
    study_sessions,
    modules,
    mock_lms,
    workflow,
    support_requests,
    moodle,
)
from lms.database import CONFIGURED_LMS_DATABASE_URL, LMSBase, LMSSessionLocal, lms_engine
from lms.generator import ensure_mock_lms_seeded, lms_dataset_is_seeded
import lms.models
from lms.workflow_service import ensure_fictional_student_emails
from app.observability import RequestObservabilityMiddleware, get_app_logger
from app.services.firebase_auth import get_firebase_app
import os

logger = get_app_logger()

app = FastAPI(
    title="NeuroSync API",
    description="AI University Intelligence Platform — Backend REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestObservabilityMiddleware)

if settings.environment == "production":
    get_firebase_app()

# Create tables
Base.metadata.create_all(bind=engine)
LMSBase.metadata.create_all(bind=lms_engine)

# Bootstrap the synthetic Mock LMS dataset on first run so every lecturer and
# advisor view is backed by LMS records. Set NEUROSYNC_AUTO_SEED_LMS=0 to skip
# and generate manually with: python -m lms.mock_data --recreate
if os.getenv("NEUROSYNC_AUTO_SEED_LMS", "1") != "0" and CONFIGURED_LMS_DATABASE_URL is None:
    lms_engine.dispose()
    try:
        if not lms_dataset_is_seeded():
            logger.info("mock_lms_seed_started", extra={"event": "mock_lms_seed_started"})
        seeding_summary = ensure_mock_lms_seeded()
        if seeding_summary:
            logger.info(
                "mock_lms_seed_completed",
                extra={
                    "event": "mock_lms_seed_completed",
                    "student_count": seeding_summary["student_count"],
                    "module_count": seeding_summary["module_count"],
                    "assessment_count": seeding_summary["assessment_count"],
                },
            )
    except Exception as seeding_error:  # pragma: no cover - demo bootstrap only
        logger.error(
            "mock_lms_seed_failed",
            extra={"event": "mock_lms_seed_failed", "error_type": type(seeding_error).__name__},
        )

if settings.environment != "production":
    lms_db = LMSSessionLocal()
    try:
        ensure_fictional_student_emails(lms_db)
    finally:
        lms_db.close()

# Register routers
app.include_router(auth.router)
app.include_router(admin_users.router)
app.include_router(csv_data.router)
app.include_router(health.router)
app.include_router(students.router)
app.include_router(assessments.router)
app.include_router(attendance.router)
app.include_router(wellbeing.router)
app.include_router(predictions.router)
app.include_router(analytics.router)
app.include_router(study_sessions.router)
app.include_router(modules.router)
app.include_router(mock_lms.router)
app.include_router(workflow.router)
app.include_router(support_requests.router)
app.include_router(moodle.router)
