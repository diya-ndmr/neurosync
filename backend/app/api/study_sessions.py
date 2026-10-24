from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.student import StudentProfile
from app.models.study_session import StudySession
from app.models.user import User, UserRole
from app.schemas.record_schema import StudySessionCreate
from app.middleware.security import get_current_user, require_own_student_record

router = APIRouter(prefix="/api", tags=["Study Sessions"])


@router.post("/study-sessions")
def create_study_session(
    data: StudySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_own_student_record(current_user, data.student_id, db)
    if not db.query(StudentProfile.id).filter(StudentProfile.id == data.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    session = StudySession(
        student_id=data.student_id,
        subject=data.subject,
        duration_minutes=data.duration_minutes,
        activity_type=data.activity_type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"message": "Study session recorded", "id": session.id}


@router.get("/students/{student_id}/study-sessions")
def get_student_study_sessions(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_own_student_record(current_user, student_id, db)
    sessions = (
        db.query(StudySession)
        .filter(StudySession.student_id == student_id)
        .order_by(StudySession.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "subject": s.subject,
            "duration_minutes": s.duration_minutes,
            "activity_type": s.activity_type,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in sessions
    ]
