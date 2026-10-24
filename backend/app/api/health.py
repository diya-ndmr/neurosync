import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import engine
from lms.database import lms_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


def _database_is_available(database_name: str, database_engine: Engine) -> bool:
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database readiness probe failed for %s", database_name)
        return False
    return True


@router.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "NeuroSync API", "version": "1.0.0"}


@router.get("/api/ready")
def readiness_check():
    checks = {
        "application_database": "ready" if _database_is_available("application", engine) else "unavailable",
        "lms_database": "ready" if _database_is_available("lms", lms_engine) else "unavailable",
    }
    if any(check != "ready" for check in checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}