from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.mood_checkin import MoodCheckin
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.record_schema import WellbeingCheckinCreate
from app.middleware.security import get_current_user, require_own_student_record

router = APIRouter(prefix="/api/wellbeing", tags=["Wellbeing"])


@router.post("/checkin")
def checkin(
    data: WellbeingCheckinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_own_student_record(current_user, data.student_id, db)
    if not db.query(StudentProfile.id).filter(StudentProfile.id == data.student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    checkin = MoodCheckin(
        student_id=data.student_id,
        mood_score=data.mood_score,
        stress_level=data.stress_level,
        notes=data.notes,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return {"message": "Check-in saved", "id": checkin.id}


@router.get("/{student_id}")
def get_wellbeing_history(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_own_student_record(current_user, student_id, db)
    history = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.student_id == student_id)
        .order_by(MoodCheckin.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": h.id,
            "mood_score": h.mood_score,
            "stress_level": h.stress_level,
            "notes": h.notes,
            "created_at": h.created_at.isoformat() if h.created_at else "",
        }
        for h in history
    ]
