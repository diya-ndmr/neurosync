from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.assessment import Assessment
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.record_schema import AssessmentCreate
from app.middleware.security import require_own_student_record, require_role

router = APIRouter(prefix="/api", tags=["Assessments"])


def _require_student_and_module(db: Session, student_id: str, module_id: str) -> None:
    """Reject orphan rows instead of writing a record no view can resolve."""
    if not db.query(StudentProfile.id).filter(StudentProfile.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if not db.query(Module.id).filter(Module.id == module_id).first():
        raise HTTPException(status_code=404, detail="Module not found")


@router.post("/assessments")
def create_assessment(
    data: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    _require_student_and_module(db, data.student_id, data.module_id)
    assessment = Assessment(
        student_id=data.student_id,
        module_id=data.module_id,
        assessment_type=data.assessment_type,
        mark=data.mark,
        assessment_date=data.assessment_date,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return {"message": "Assessment created", "id": assessment.id}


@router.get("/students/{student_id}/assessments")
def get_student_assessments(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    require_own_student_record(current_user, student_id, db)
    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id)
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "module": a.module.module_name if a.module else "Unknown",
            "module_code": a.module.module_code if a.module else "",
            "assessment_type": a.assessment_type,
            "mark": a.mark,
            "assessment_date": a.assessment_date.isoformat() if a.assessment_date else "",
        }
        for a in assessments
    ]
