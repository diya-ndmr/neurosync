import json
import math
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import engine, get_db
from app.middleware.security import require_role
from app.models.audit_event import AuditEvent
from app.models.csv_import_history import CsvImportHistory
from app.models.user import UserRole
from app.services.moodle_service import get_safe_moodle_base_url, is_moodle_configured
from lms.database import lms_engine

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin console"],
    dependencies=[Depends(require_role(UserRole.admin))],
)

METRICS_PATH = Path(__file__).resolve().parents[3] / "ml" / "models" / "metrics.json"


def _database_status(database_engine) -> str:
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except SQLAlchemyError:
        return "failed"


@router.get("/model-performance")
def model_performance() -> dict[str, Any]:
    try:
        with METRICS_PATH.open(encoding="utf-8") as metrics_file:
            artifact = json.load(metrics_file)
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Model evaluation metrics are unavailable.") from error

    if not isinstance(artifact, dict) or not isinstance(artifact.get("results", {}), dict):
        raise HTTPException(status_code=503, detail="Model evaluation metrics have an invalid format.")
    best_model = artifact.get("best_model")
    results = artifact.get("results", {})
    metrics = results.get(best_model, {}) if isinstance(best_model, str) else {}
    if not isinstance(metrics, dict):
        raise HTTPException(status_code=503, detail="Model evaluation metrics have an invalid format.")

    def actual_metric(key: str) -> float | None:
        value = metrics.get(key)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None

    return {
        "model_name": best_model,
        "precision": actual_metric("precision_weighted"),
        "recall": actual_metric("recall_weighted"),
        "f1_score": actual_metric("f1_weighted"),
        "evaluated_at": artifact.get("evaluated_at"),
        "training_data_source": artifact.get("training_data_source", "Synthetic student risk dataset"),
        "validation_status": "prototype_not_validated_on_real_student_data",
    }


@router.get("/security")
def security_overview() -> dict[str, Any]:
    return {
        "permissions": [
            {
                "role": "lecturer",
                "enforcement": "Backend role checks on lecturer review, attendance and support routes; endpoint scope checks also apply.",
            },
            {
                "role": "advisor",
                "enforcement": "Backend role checks on advisor case, referral and intervention routes; endpoint scope checks also apply.",
            },
            {
                "role": "admin",
                "enforcement": "Backend role checks on user management, CSV, audit, integration and administration endpoints.",
            },
        ],
        "mfa": {
            "status": "not_integrated",
            "detail": "The application does not currently verify staff MFA enrollment or assurance state.",
        },
        "encryption": {
            "production_https_required": True,
            "frontend_https_configured": settings.frontend_url.startswith("https://"),
            "supabase_https_configured": (
                settings.supabase_url.startswith("https://") if settings.supabase_url else None
            ),
            "database_transport": "not_verified",
            "encryption_at_rest": "not_verifiable_from_application",
        },
        "audit_log": {"available": True, "retention": "not_configured"},
        "data_retention": {
            "status": "not_configured",
            "detail": "No retention duration or data scope is configured or enforced.",
        },
        "privacy_notice": {
            "status": "institutional_notice_not_configured",
            "detail": "Add the institution-approved privacy notice and processing purpose before production use.",
        },
    }


@router.get("/audit-events")
def audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(AuditEvent).order_by(AuditEvent.occurred_at.desc())
    total = query.count()
    events = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "event_id": event.event_id,
                "actor": event.actor_reference,
                "action": event.action,
                "outcome": event.outcome,
                "occurred_at": event.occurred_at,
            }
            for event in events
        ],
    }


@router.get("/integrations")
def integrations_overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    import_events = (
        db.query(CsvImportHistory)
        .order_by(CsvImportHistory.occurred_at.desc())
        .limit(25)
        .all()
    )
    configured = is_moodle_configured()
    return {
        "api_status": "connected",
        "application_database_status": _database_status(engine),
        "lms_database_status": _database_status(lms_engine),
        "moodle": {
            "configured": configured,
            "base_url": get_safe_moodle_base_url() if configured else None,
            "connection_status": "ready_to_test" if configured else "not_configured",
            "last_successful_sync": None,
            "sync_available": False,
            "sync_unavailable_reason": "No Moodle data mappings or synchronization workflow are configured.",
        },
        "csv_import_history": [
            {
                "event_id": event.import_id,
                "dataset": event.dataset,
                "outcome": event.outcome,
                "occurred_at": event.occurred_at,
                "validation_error": bool(event.errors),
                "invalid_rows": event.invalid_rows,
                "persisted_rows": event.persisted_rows,
                "errors": event.errors,
                "errors_truncated": event.errors_truncated,
            }
            for event in import_events
        ],
    }
