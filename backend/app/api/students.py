from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.student_schema import StudentProfileResponse, StudentDashboardResponse
from app.middleware.security import require_own_student_record, require_role
from app.services.prediction_service import get_student_dashboard

router = APIRouter(prefix="/api/students", tags=["Students"])


def _profile_json(student: StudentProfile) -> StudentProfileResponse:
    return StudentProfileResponse(
        id=student.id,
        user_id=student.user_id,
        student_number=student.student_number,
        first_name=student.first_name,
        surname=student.surname,
        programme=student.programme,
        year_level=student.year_level,
        created_at=student.created_at.isoformat() if student.created_at else "",
    )


@router.get("/me", response_model=StudentProfileResponse)
def get_my_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    """Resolve the profile linked to the signed-in student account.

    The web client needs its own profile id before it can request dashboards,
    attendance or assessments; without this it had to hard-code a demo id.
    Declared before ``/{student_id}`` so "me" is not parsed as an identifier.
    """
    student = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="No student profile is linked to this account")
    return _profile_json(student)


@router.get("/{student_id}", response_model=StudentProfileResponse)
def get_student_profile(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    require_own_student_record(current_user, student_id, db)
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return _profile_json(student)


@router.get("/{student_id}/dashboard")
def get_dashboard(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    require_own_student_record(current_user, student_id, db)
    data = get_student_dashboard(db, student_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data
