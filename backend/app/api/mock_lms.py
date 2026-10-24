from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.middleware.security import require_role
from app.models.user import User, UserRole
from lms.database import LMSSessionLocal, get_lms_database_url
from lms.models import AttendanceRecord, AssessmentResult, LMSActivity, Module, ModuleEnrolment, QuizAttempt, Referral, StaffMapping, Student, StudentMapping

router = APIRouter(prefix="/api/lms", tags=["Mock LMS"])
_STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _get_lms_db():
    db = LMSSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _authorise_student(db: Session, current_user: User, student_id: str, module_id: str | None = None) -> None:
    if current_user.role == UserRole.admin:
        return
    if current_user.role == UserRole.student:
        mapping = db.query(StudentMapping).filter(StudentMapping.app_user_email == current_user.email.lower()).first()
        if mapping and mapping.student_id == student_id:
            return
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == UserRole.lecturer:
        mapping = db.query(StaffMapping).filter(StaffMapping.app_user_email == current_user.email.lower()).first()
        if not mapping:
            raise HTTPException(status_code=403, detail="No authorised LMS lecturer mapping is configured")
        taught_modules = db.query(Module.module_id).filter(Module.lecturer_id == mapping.lecturer_id)
        query = db.query(ModuleEnrolment).filter(
            ModuleEnrolment.student_id == student_id,
            ModuleEnrolment.module_id.in_(taught_modules),
        )
        if module_id:
            query = query.filter(ModuleEnrolment.module_id == module_id)
        if query.first():
            return
        raise HTTPException(status_code=404, detail="Student not found in your authorised teaching scope")
    if current_user.role == UserRole.advisor:
        query = db.query(Referral).filter(
            Referral.student_id == student_id,
            (Referral.advisor_user_id == current_user.id) | (Referral.advisor_user_id.is_(None)),
        )
        if query.first():
            return
        raise HTTPException(status_code=404, detail="Student not found in your authorised case scope")
    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get("/students")
def list_students(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    query = db.query(Student)
    if current_user.role == UserRole.student:
        mapping = db.query(StudentMapping).filter(StudentMapping.app_user_email == current_user.email.lower()).first()
        if not mapping:
            raise HTTPException(status_code=403, detail="No authorised LMS student mapping is configured")
        query = query.filter(Student.student_id == mapping.student_id)
    elif current_user.role == UserRole.lecturer:
        mapping = db.query(StaffMapping).filter(StaffMapping.app_user_email == current_user.email.lower()).first()
        if not mapping:
            raise HTTPException(status_code=403, detail="No authorised LMS lecturer mapping is configured")
        taught_modules = db.query(ModuleEnrolment.student_id).join(Module).filter(Module.lecturer_id == mapping.lecturer_id)
        query = query.filter(Student.student_id.in_(taught_modules))
    elif current_user.role == UserRole.advisor:
        pass  # advisors see all students to enable intelligent triage and case assignment
    students = query.order_by(Student.student_id).offset(offset).limit(limit).all()
    total = query.count()
    return {
        "items": [
            {
                "student_id": s.student_id,
                "first_name": s.first_name,
                "surname": s.surname,
                "institutional_email": s.institutional_email,
                "programme_id": s.programme_id,
                "year_of_study": s.year_of_study,
                "semester": s.semester,
                "enrolment_status": s.enrolment_status,
            }
            for s in students
        ],
        "offset": offset,
        "limit": limit,
        "total": total,
    }

def get_student(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    if not _STUDENT_ID_PATTERN.fullmatch(student_id):
        raise HTTPException(status_code=400, detail="Malformed student ID")
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _authorise_student(db, current_user, student_id)
    return {
        "student_id": student.student_id,
        "first_name": student.first_name,
        "surname": student.surname,
        "institutional_email": student.institutional_email,
        "programme_id": student.programme_id,
        "year_of_study": student.year_of_study,
        "semester": student.semester,
        "enrolment_status": student.enrolment_status,
    }


@router.get("/students/{student_id}/attendance")
def get_student_attendance(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    if not _STUDENT_ID_PATTERN.fullmatch(student_id):
        raise HTTPException(status_code=400, detail="Malformed student ID")
    _authorise_student(db, current_user, student_id)
    records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).all()
    return {"student_id": student_id, "items": [
        {
            "attendance_id": r.attendance_id,
            "module_id": r.module_id,
            "session_date": r.session_date.isoformat(),
            "status": r.status,
        } for r in records
    ]}


@router.get("/students/{student_id}/assessments")
def get_student_assessments(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    _authorise_student(db, current_user, student_id)
    results = db.query(AssessmentResult).filter(AssessmentResult.student_id == student_id).all()
    return {"student_id": student_id, "items": [
        {
            "result_id": r.result_id,
            "assessment_id": r.assessment_id,
            "mark": r.mark,
            "percentage": r.percentage,
            "submission_date": r.submission_date.isoformat() if r.submission_date else None,
            "status": r.status,
        } for r in results
    ]}


@router.get("/students/{student_id}/quizzes")
def get_student_quizzes(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    _authorise_student(db, current_user, student_id)
    attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
    return {"student_id": student_id, "items": [
        {
            "attempt_id": a.attempt_id,
            "quiz_id": a.quiz_id,
            "attempt_number": a.attempt_number,
            "score": a.score,
            "percentage": a.percentage,
            "started_at": a.started_at.isoformat(),
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "duration": a.duration,
        } for a in attempts
    ]}


@router.get("/students/{student_id}/engagement")
def get_student_engagement(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    _authorise_student(db, current_user, student_id)
    activity = db.query(LMSActivity).filter(LMSActivity.student_id == student_id).order_by(LMSActivity.timestamp).all()
    return {
        "student_id": student_id,
        "items": [{
            "activity_id": a.activity_id,
            "timestamp": a.timestamp.isoformat(),
            "activity_type": a.activity_type,
            "module_id": a.module_id,
            "session_duration": a.session_duration,
        } for a in activity],
        "total": len(activity),
    }


@router.get("/students/{student_id}/modules")
def get_student_modules(
    student_id: str,
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    _authorise_student(db, current_user, student_id)
    rows = db.query(ModuleEnrolment).filter(ModuleEnrolment.student_id == student_id).all()
    return {"student_id": student_id, "items": [{"enrolment_id": r.enrolment_id, "module_id": r.module_id, "status": r.status} for r in rows]}


@router.get("/modules/{module_id}/students")
def get_module_students(
    module_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(_get_lms_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    if current_user.role == UserRole.lecturer:
        mapping = db.query(StaffMapping).filter(StaffMapping.app_user_email == current_user.email.lower()).first()
        if not mapping or not db.query(Module).filter(Module.module_id == module_id, Module.lecturer_id == mapping.lecturer_id).first():
            raise HTTPException(status_code=404, detail="Module not found in your authorised teaching scope")
    rows = db.query(ModuleEnrolment).filter(ModuleEnrolment.module_id == module_id).offset(offset).limit(limit).all()
    return {
        "module_id": module_id,
        "items": [{"student_id": r.student_id, "status": r.status} for r in rows],
        "offset": offset,
        "limit": limit,
        "total": db.query(ModuleEnrolment).filter(ModuleEnrolment.module_id == module_id).count(),
    }


@router.get("/health")
def lms_health():
    return {"status": "healthy", "service": "Mock LMS", "database": get_lms_database_url()}
