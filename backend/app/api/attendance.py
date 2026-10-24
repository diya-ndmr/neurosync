from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.attendance import Attendance
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.schemas.record_schema import AttendanceCreate
from app.middleware.security import require_own_student_record, require_role

router = APIRouter(prefix="/api", tags=["Attendance"])


def _require_student_and_module(db: Session, student_id: str, module_id: str) -> None:
    """Reject orphan rows instead of writing a record no view can resolve."""
    if not db.query(StudentProfile.id).filter(StudentProfile.id == student_id).first():
        raise HTTPException(status_code=404, detail="Student not found")
    if not db.query(Module.id).filter(Module.id == module_id).first():
        raise HTTPException(status_code=404, detail="Module not found")


@router.post("/attendance")
def record_attendance(
    data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    _require_student_and_module(db, data.student_id, data.module_id)
    attendance = Attendance(
        student_id=data.student_id,
        module_id=data.module_id,
        attendance_percentage=data.attendance_percentage,
        date=data.date,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return {"message": "Attendance recorded", "id": attendance.id}


@router.get("/students/{student_id}/attendance")
def get_student_attendance(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    require_own_student_record(current_user, student_id, db)
    records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "module": a.module.module_name if a.module else "Unknown",
            "module_code": a.module.module_code if a.module else "",
            "attendance_percentage": a.attendance_percentage,
            "date": a.date.isoformat() if a.date else "",
        }
        for a in records
    ]
