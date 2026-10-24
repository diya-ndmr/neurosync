from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User, UserRole
from app.middleware.security import require_role
from app.services.analytics_service import get_admin_analytics, get_admin_analytics_lms, get_radar_insights, get_recovering_students
from app.schemas.analytics_schema import AdminIntelligenceQuestion
from app.services.analytics_service import answer_admin_intelligence_question
from lms.database import LMSSessionLocal
from lms.models import WorkbookIntelligence
import json

router = APIRouter(prefix="/api/admin", tags=["Analytics"])


@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    # Use LMS database which has the 500 imported students
    lms_db = LMSSessionLocal()
    try:
        return get_admin_analytics_lms(lms_db)
    finally:
        lms_db.close()


@router.get("/recovering-students")
def get_students_recovering(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return {"items": get_recovering_students(db, limit=max(1, min(limit, 100)))}


@router.get("/workbook-intelligence")
def get_workbook_intelligence(
    sheet: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.admin)),
):
    lms_db = LMSSessionLocal()
    try:
        query = lms_db.query(WorkbookIntelligence)
        if sheet:
            query = query.filter(WorkbookIntelligence.sheet_name == sheet)
        rows = query.order_by(WorkbookIntelligence.row_number).limit(max(1, min(limit, 1000))).all()
        return {"items": [{"sheet": row.sheet_name, **json.loads(row.payload)} for row in rows]}
    finally:
        lms_db.close()


@router.get("/radar")
def get_radar(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return {"items": get_radar_insights(db, limit=max(1, min(limit, 100)))}


@router.post("/ask")
def ask_neurosync(
    data: AdminIntelligenceQuestion,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    return answer_admin_intelligence_question(db, data.question)
