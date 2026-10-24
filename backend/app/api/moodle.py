from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.security import require_role
from app.models.user import UserRole
from app.services.moodle_service import (
    MoodleConfigurationError,
    MoodleConnectionError,
    get_safe_moodle_base_url,
    is_moodle_configured,
    test_moodle_connection,
)

router = APIRouter(
    prefix="/api/moodle",
    tags=["Moodle"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


@router.get("/status")
def moodle_status():
    configured = is_moodle_configured()
    return {
        "configured": configured,
        "base_url": get_safe_moodle_base_url() if configured else None,
        "connection_status": "ready_to_test" if configured else "not_configured",
    }


@router.post("/test")
def test_moodle_connection_endpoint():
    try:
        result = test_moodle_connection()
    except (MoodleConfigurationError, MoodleConnectionError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from None
    return {
        "connected": True,
        "connection_status": "connected",
        **result,
    }
