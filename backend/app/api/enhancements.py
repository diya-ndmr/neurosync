from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.middleware.security import get_current_user, require_role
from app.models import (
    Assessment,
    ClassAttendanceRecord,
    LearningProgress,
    LearningResource,
    LearningTopic,
    Module,
    StudentProfile,
    TopicFeedback,
    UserPreference,
    WellnessAppointment,
    WellnessAppointmentSlot,
    WellnessReferral,
)
from app.models.user import User, UserRole
from app.schemas.enhancement_schema import (
    AppointmentBookingCreate,
    AppointmentSlotCreate,
    AppointmentSlotUpdate,
    AppointmentStatusUpdate,
    ClassAttendanceCreate,
    LearningProgressUpdate,
    ResourceLinkCreate,
    TopicCreate,
    TopicFeedbackCreate,
    UserPreferencesUpdate,
    WellnessReferralCreate,
    WellnessReferralStatusUpdate,
)
from app.services.audit_service import record_audit_event
from lms.database import LMSSessionLocal
from lms.models import Module as LmsModule
from lms.models import ModuleEnrolment, Referral as LmsReferral, StaffMapping, StudentMapping

router = APIRouter(prefix="/api", tags=["Learning support, attendance and wellbeing"])
MAX_RESOURCE_BYTES = 10 * 1024 * 1024
ALLOWED_RESOURCE_EXTENSIONS = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".md"}
EXCLUDED_ATTENDANCE = {"excused", "approved_leave"}
ATTENDED_STATUSES = {"present", "late"}


def _audit(db: Session, user: User, action: str) -> None:
    record_audit_event(
        db,
        action=action,
        outcome="SUCCESS",
        actor_reference=user.email.lower(),
        actor_id=user.id,
    )


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _student_scope(db: Session, user: User, student_id: str) -> StudentProfile:
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if user.role == UserRole.student and student.user_id != user.id:
        raise HTTPException(status_code=403, detail="Students may only access their own records")
    if user.role == UserRole.advisor:
        lms_db = LMSSessionLocal()
        try:
            mapping = lms_db.query(StudentMapping).filter(
                StudentMapping.app_user_email == student.user.email.lower()
            ).first()
            if mapping is None or not lms_db.query(LmsReferral).filter(
                LmsReferral.student_id == mapping.student_id,
                (LmsReferral.advisor_user_id == user.id) | (LmsReferral.advisor_user_id.is_(None)),
            ).first():
                raise HTTPException(status_code=404, detail="Student has no support case in your authorised scope")
        finally:
            lms_db.close()
    return student


def _module_scope(user: User, module: Module, student: Optional[StudentProfile] = None) -> None:
    if user.role == UserRole.admin:
        return
    if user.role not in (UserRole.lecturer, UserRole.student):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    lms_db = LMSSessionLocal()
    try:
        lms_modules = lms_db.query(LmsModule).filter(LmsModule.module_code == module.module_code).all()
        if user.role == UserRole.lecturer:
            mapping = lms_db.query(StaffMapping).filter(
                StaffMapping.app_user_email == user.email.lower()
            ).first()
            if mapping is None or not any(item.lecturer_id == mapping.lecturer_id for item in lms_modules):
                raise HTTPException(status_code=403, detail="Module is outside your authorised teaching scope")
            if student is not None:
                student_user = student.user
                student_mapping = lms_db.query(StudentMapping).filter(
                    StudentMapping.app_user_email == student_user.email.lower()
                ).first()
                if student_mapping is None or not lms_db.query(ModuleEnrolment).filter(
                    ModuleEnrolment.student_id == student_mapping.student_id,
                    ModuleEnrolment.module_id.in_([item.module_id for item in lms_modules]),
                ).first():
                    raise HTTPException(status_code=404, detail="Student is not enrolled in this module")
        else:
            student_user = student.user if student is not None else user
            student_mapping = lms_db.query(StudentMapping).filter(
                StudentMapping.app_user_email == student_user.email.lower()
            ).first()
            if student_mapping is None or not lms_db.query(ModuleEnrolment).filter(
                ModuleEnrolment.student_id == student_mapping.student_id,
                ModuleEnrolment.module_id.in_([item.module_id for item in lms_modules]),
            ).first():
                raise HTTPException(status_code=404, detail="Module is outside your enrolled course scope")
    finally:
        lms_db.close()


def _topic_scope(db: Session, user: User, topic_id: str, student: Optional[StudentProfile] = None) -> LearningTopic:
    topic = db.query(LearningTopic).filter(LearningTopic.id == topic_id).first()
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    module = db.query(Module).filter(Module.id == topic.module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module, student)
    return topic


def _wellness_referral_scope(
    db: Session, user: User, referral_id: str, *, assign_if_unassigned: bool = False
) -> WellnessReferral:
    referral = db.query(WellnessReferral).filter(WellnessReferral.id == referral_id).first()
    if referral is None:
        raise HTTPException(status_code=404, detail="Wellness referral not found")
    if user.role == UserRole.advisor:
        if referral.assigned_to not in (None, user.id):
            raise HTTPException(status_code=404, detail="Wellness referral not found")
        if assign_if_unassigned and referral.assigned_to is None:
            referral.assigned_to = user.id
    return referral


def _resource_json(resource: LearningResource, status_value: Optional[str] = None) -> dict:
    return {
        "id": resource.id,
        "topic_id": resource.topic_id,
        "title": resource.title,
        "description": resource.description,
        "resource_type": resource.resource_type,
        "url": resource.resource_url if resource.resource_type == "link" else f"/api/learning/resources/{resource.id}/download",
        "filename": resource.original_filename,
        "provider": resource.provider,
        "reviewed_by_lecturer": resource.reviewed_by_lecturer,
        "recommended_reason": resource.recommended_reason,
        "status": status_value,
        "created_at": resource.created_at.isoformat(),
    }


def _attendance_summary(records: list[ClassAttendanceRecord], start: date, today: date) -> dict:
    eligible = [row for row in records if row.status not in EXCLUDED_ATTENDANCE]

    def percentage(rows: list[ClassAttendanceRecord]) -> Optional[int]:
        valid = [row for row in rows if row.status not in EXCLUDED_ATTENDANCE]
        return round(sum(row.status in ATTENDED_STATUSES for row in valid) / len(valid) * 100) if valid else None

    month_rows = []
    for offset in range(3):
        period_start = start + timedelta(days=offset * 30)
        period_end = min(period_start + timedelta(days=30), today + timedelta(days=1))
        month_records = [row for row in records if period_start <= row.class_date < period_end]
        month_rows.append({
            "month": f"Month {offset + 1}",
            "period_start": period_start.isoformat(),
            "period_end": (period_end - timedelta(days=1)).isoformat(),
            "percentage": percentage(month_records),
            "attended": sum(row.status in ATTENDED_STATUSES for row in month_records),
            "classes": sum(row.status not in EXCLUDED_ATTENDANCE for row in month_records),
        })
    attended = sum(row.status in ATTENDED_STATUSES for row in eligible)
    return {
        "period_start": start.isoformat(),
        "period_end": today.isoformat(),
        "attendance_rate": percentage(records),
        "classes_attended": attended,
        "classes_counted": len(eligible),
        "excused_absences": sum(row.status in EXCLUDED_ATTENDANCE for row in records),
        "monthly_breakdown": month_rows,
        "records": [{
            "id": row.id,
            "module": row.module.module_name if row.module else "Unknown",
            "module_code": row.module.module_code if row.module else "",
            "class_name": row.class_name,
            "date": row.class_date.isoformat(),
            "status": row.status,
        } for row in sorted(records, key=lambda item: item.class_date, reverse=True)],
    }


@router.get("/learning/modules")
def learning_modules(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.student, UserRole.admin)),
):
    modules = db.query(Module).order_by(Module.module_name).all()
    available = []
    for module in modules:
        try:
            _module_scope(user, module, user.student_profile if user.role == UserRole.student else None)
        except HTTPException as error:
            if error.status_code in (403, 404):
                continue
            raise
        available.append({"id": module.id, "module_code": module.module_code, "module_name": module.module_name})
    return available


@router.get("/learning/modules/{module_id}/topics")
def get_topics(
    module_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.student, UserRole.admin)),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module, user.student_profile if user.role == UserRole.student else None)
    return [{
        "id": topic.id, "module_id": topic.module_id, "name": topic.name,
        "description": topic.description,
    } for topic in db.query(LearningTopic).filter(LearningTopic.module_id == module_id).order_by(LearningTopic.name).all()]


@router.get("/learning/modules/{module_id}/students")
def learning_module_students(
    module_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module)
    lms_db = LMSSessionLocal()
    try:
        lms_modules = lms_db.query(LmsModule).filter(LmsModule.module_code == module.module_code).all()
        lms_module_ids = [row.module_id for row in lms_modules]
        if not lms_module_ids:
            return []
        enrolments = lms_db.query(ModuleEnrolment).filter(
            ModuleEnrolment.module_id.in_(lms_module_ids),
            ModuleEnrolment.status.in_(("ENROLLED", "ACTIVE")),
        ).all()
        student_ids = [row.student_id for row in enrolments]
        mappings = lms_db.query(StudentMapping).filter(StudentMapping.student_id.in_(student_ids)).all()
        emails = [row.app_user_email.lower() for row in mappings]
    finally:
        lms_db.close()
    profiles = db.query(StudentProfile).join(User).filter(
        User.email.in_(emails)
    ).order_by(StudentProfile.surname, StudentProfile.first_name).all() if emails else []
    return [{
        "id": row.id,
        "name": f"{row.first_name} {row.surname}",
        "student_number": row.student_number,
    } for row in profiles]


@router.post("/learning/topics", status_code=status.HTTP_201_CREATED)
def create_topic(
    data: TopicCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    module = db.query(Module).filter(Module.id == data.module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module)
    if not data.name.strip():
        raise HTTPException(status_code=422, detail="A topic name is required")
    topic = LearningTopic(module_id=module.id, name=data.name.strip(), description=data.description)
    db.add(topic)
    _audit(db, user, "LEARNING_TOPIC_CREATED")
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This topic already exists in the module") from error
    db.refresh(topic)
    return {"id": topic.id, "module_id": topic.module_id, "name": topic.name, "description": topic.description}


@router.post("/learning/feedback", status_code=status.HTTP_201_CREATED)
def record_topic_feedback(
    data: TopicFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    student = _student_scope(db, user, data.student_id)
    topic = _topic_scope(db, user, data.topic_id, student)
    learning_gaps = [value.strip() for value in data.learning_gaps if value.strip()]
    if not learning_gaps or not data.feedback.strip():
        raise HTTPException(status_code=422, detail="Specific learning gaps and feedback are required")
    feedback = TopicFeedback(
        topic_id=topic.id, student_id=student.id, lecturer_id=user.id,
        strengths=[value.strip() for value in data.strengths if value.strip()],
        learning_gaps=learning_gaps,
        feedback=data.feedback.strip(), learning_goal=data.learning_goal,
        goal_due_date=data.goal_due_date,
    )
    db.add(feedback)
    _audit(db, user, "TOPIC_FEEDBACK_RECORDED")
    db.commit()
    db.refresh(feedback)
    return {"id": feedback.id, "created_at": feedback.created_at.isoformat()}


@router.post("/learning/resources/link", status_code=status.HTTP_201_CREATED)
def add_learning_link(
    data: ResourceLinkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    topic = _topic_scope(db, user, data.topic_id)
    if not data.title.strip():
        raise HTTPException(status_code=422, detail="A resource title is required")
    resource = LearningResource(
        topic_id=topic.id, uploaded_by=user.id, title=data.title.strip(),
        description=data.description, resource_type="link", resource_url=str(data.url),
        provider="lecturer", reviewed_by_lecturer=True,
    )
    db.add(resource)
    _audit(db, user, "LEARNING_RESOURCE_ADDED")
    db.commit()
    db.refresh(resource)
    return _resource_json(resource)


@router.post("/learning/resources/upload", status_code=status.HTTP_201_CREATED)
async def upload_learning_resource(
    topic_id: str,
    title: str,
    description: Optional[str] = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    topic = _topic_scope(db, user, topic_id)
    if not title.strip():
        raise HTTPException(status_code=422, detail="A resource title is required")
    if len(title.strip()) > 200:
        raise HTTPException(status_code=422, detail="Resource titles must be 200 characters or shorter")
    if description is not None and len(description) > 1000:
        raise HTTPException(status_code=422, detail="Resource descriptions must be 1,000 characters or shorter")
    original_filename = Path((file.filename or "").replace("\\", "/")).name.strip()
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_RESOURCE_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PDF, Office documents, text and Markdown resources are accepted")
    if not original_filename or len(original_filename) > 255 or any(ord(character) < 32 for character in original_filename):
        raise HTTPException(status_code=422, detail="The resource filename is invalid")
    content = await file.read(MAX_RESOURCE_BYTES + 1)
    if len(content) > MAX_RESOURCE_BYTES:
        raise HTTPException(status_code=413, detail="Learning resources must be 10 MB or smaller")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded resource is empty")
    resource = LearningResource(
        topic_id=topic.id, uploaded_by=user.id, title=title.strip(), description=description,
        resource_type="file", original_filename=original_filename,
        file_data=content, provider="lecturer", reviewed_by_lecturer=True,
    )
    db.add(resource)
    _audit(db, user, "LEARNING_RESOURCE_UPLOADED")
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(resource)
    return _resource_json(resource)


@router.get("/learning/resources/{resource_id}/download")
def download_learning_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if resource is None or resource.resource_type != "file" or not resource.file_data:
        raise HTTPException(status_code=404, detail="Learning resource not found")
    _topic_scope(db, user, resource.topic_id, user.student_profile if user.role == UserRole.student else None)
    return Response(
        content=resource.file_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment"},
    )


@router.get("/students/{student_id}/learning-support")
def student_learning_support(
    student_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    student = _student_scope(db, user, student_id)
    feedback_rows = db.query(TopicFeedback).filter(
        TopicFeedback.student_id == student.id
    ).order_by(TopicFeedback.created_at.desc()).all()
    response = []
    seen_topics = set()
    for feedback in feedback_rows:
        if feedback.topic_id in seen_topics:
            continue
        seen_topics.add(feedback.topic_id)
        topic = feedback.topic
        _module_scope(user, topic.module, student)
        module_marks = [row.mark for row in db.query(Assessment).filter(
            Assessment.student_id == student.id,
            Assessment.module_id == topic.module_id,
        ).all()]
        average_mark = round(sum(module_marks) / len(module_marks), 1) if module_marks else None
        resources = []
        visible_resources = db.query(LearningResource).filter(
            LearningResource.topic_id == topic.id,
            (LearningResource.assigned_student_id.is_(None)) | (LearningResource.assigned_student_id == student.id),
        ).order_by(LearningResource.display_priority.desc(), LearningResource.created_at.desc()).all()
        for resource in visible_resources:
            progress = db.query(LearningProgress).filter(
                LearningProgress.student_id == student.id,
                LearningProgress.resource_id == resource.id,
            ).first()
            resources.append(_resource_json(resource, progress.status if progress else "new"))
        response.append({
            "feedback_id": feedback.id,
            "module_id": topic.module_id,
            "module": topic.module.module_name,
            "topic_id": topic.id,
            "topic": topic.name,
            "strengths": feedback.strengths,
            "learning_gaps": feedback.learning_gaps,
            "feedback": feedback.feedback,
            "learning_goal": feedback.learning_goal,
            "goal_due_date": feedback.goal_due_date.isoformat() if feedback.goal_due_date else None,
            "performance_context": {
                "module_average": average_mark,
                "explanation": "Based on recorded assessments in this module." if average_mark is not None else "No assessment marks are recorded for this module yet.",
            },
            "recommendation_explanation": (
                f"These resources are linked by your lecturer to {topic.name}, "
                f"which your lecturer identified as a learning gap."
            ),
            "resources": resources,
            "mastery_claimed": False,
        })
    return response


@router.get("/students/{student_id}/support-context")
def student_support_context(
    student_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    student = _student_scope(db, user, student_id)
    module = db.query(Module).filter(Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module, student)

    today = date.today()
    recent_start = today - timedelta(days=29)
    previous_start = today - timedelta(days=59)
    module_records = db.query(ClassAttendanceRecord).filter(
        ClassAttendanceRecord.student_id == student.id,
        ClassAttendanceRecord.module_id == module.id,
        ClassAttendanceRecord.class_date >= previous_start,
        ClassAttendanceRecord.class_date <= today,
    ).all()

    def attendance_rate(rows: list[ClassAttendanceRecord]) -> Optional[int]:
        included = [row for row in rows if row.status not in EXCLUDED_ATTENDANCE]
        return round(sum(row.status in ATTENDED_STATUSES for row in included) / len(included) * 100) if included else None

    recent_records = [row for row in module_records if row.class_date >= recent_start]
    previous_records = [row for row in module_records if previous_start <= row.class_date < recent_start]
    recent_attendance = attendance_rate(recent_records)
    previous_attendance = attendance_rate(previous_records)
    attendance_change = (
        recent_attendance - previous_attendance
        if recent_attendance is not None and previous_attendance is not None
        else None
    )
    marks = [row.mark for row in db.query(Assessment).filter(
        Assessment.student_id == student.id,
        Assessment.module_id == module.id,
    ).all()]
    module_average = round(sum(marks) / len(marks), 1) if marks else None
    feedback_rows = db.query(TopicFeedback).join(LearningTopic).filter(
        TopicFeedback.student_id == student.id,
        LearningTopic.module_id == module.id,
    ).order_by(TopicFeedback.created_at.desc()).all()
    gaps = []
    for row in feedback_rows:
        gaps.extend(row.learning_gaps)
    gaps = list(dict.fromkeys(gaps))
    indicators = []
    if module_average is not None:
        indicators.append({"type": "academic_performance", "value": module_average, "label": "Recorded module assessment average"})
    if recent_attendance is not None:
        indicators.append({"type": "attendance_recent", "value": recent_attendance, "label": "Attendance in the last 30 days"})
    if attendance_change is not None:
        indicators.append({"type": "attendance_change", "value": attendance_change, "label": "Change versus the previous 30 days"})
    if gaps:
        indicators.append({"type": "lecturer_feedback", "value": gaps, "label": "Specific lecturer-identified learning gaps"})
    support_suggestion = None
    if gaps:
        support_suggestion = "A lecturer has identified specific learning gaps; review the linked topic resources with the student."
        if module_average is not None and module_average < 50:
            support_suggestion += f" The recorded module assessment average is {module_average}%; consider discussing academic support."
    elif module_average is not None and module_average < 50:
        support_suggestion = "Recorded module assessment marks are below 50%; consider discussing academic support with the student."
    return {
        "module": module.module_name,
        "indicators": indicators,
        "academic_average": module_average,
        "attendance_recent": recent_attendance,
        "attendance_previous": previous_attendance,
        "attendance_change": attendance_change,
        "learning_gaps": gaps,
        "support_suggestion": support_suggestion,
        "attendance_is_not_an_automatic_risk_label": True,
    }


@router.patch("/learning/resources/{resource_id}/progress")
def update_learning_progress(
    resource_id: str,
    data: LearningProgressUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    student = user.student_profile
    if student is None:
        raise HTTPException(status_code=404, detail="No student profile is linked to this account")
    resource = db.query(LearningResource).filter(LearningResource.id == resource_id).first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Learning resource not found")
    topic = _topic_scope(db, user, resource.topic_id, student)
    progress = db.query(LearningProgress).filter(
        LearningProgress.student_id == student.id,
        LearningProgress.resource_id == resource.id,
    ).first()
    if progress is None:
        progress = LearningProgress(student_id=student.id, resource_id=resource.id, status=data.status)
        db.add(progress)
    else:
        progress.status = data.status
    _audit(db, user, "LEARNING_RESOURCE_PROGRESS_UPDATED")
    db.commit()
    return {"resource_id": resource.id, "topic_id": topic.id, "status": progress.status}


@router.post("/attendance/classes", status_code=status.HTTP_201_CREATED)
def record_class_attendance(
    data: ClassAttendanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    student = _student_scope(db, user, data.student_id)
    module = db.query(Module).filter(Module.id == data.module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module, student)
    record = ClassAttendanceRecord(
        student_id=student.id, module_id=module.id, class_name=data.class_name.strip(),
        class_date=data.class_date, status=data.status, updated_by=user.id,
    )
    db.add(record)
    _audit(db, user, "CLASS_ATTENDANCE_RECORDED")
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Attendance for this student and class was already recorded") from error
    db.refresh(record)
    return {"id": record.id, "status": record.status}


@router.patch("/attendance/classes/{record_id}")
def correct_class_attendance(
    record_id: str,
    data: ClassAttendanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    record = db.query(ClassAttendanceRecord).filter(ClassAttendanceRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Class attendance record not found")
    student = _student_scope(db, user, record.student_id)
    _module_scope(user, record.module, student)
    if (data.student_id, data.module_id, data.class_name, data.class_date) != (
        record.student_id, record.module_id, record.class_name, record.class_date
    ):
        raise HTTPException(status_code=422, detail="Corrections may change attendance status only")
    record.status = data.status
    record.updated_by = user.id
    _audit(db, user, "CLASS_ATTENDANCE_CORRECTED")
    db.commit()
    return {"id": record.id, "status": record.status}


@router.get("/attendance/classes")
def list_class_attendance(
    module_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    _module_scope(user, module)
    records = db.query(ClassAttendanceRecord).filter(
        ClassAttendanceRecord.module_id == module_id
    ).order_by(ClassAttendanceRecord.class_date.desc()).limit(200).all()
    if user.role == UserRole.lecturer:
        records = [row for row in records if _lecturer_can_see_class(user, row, row.student)]
    return [{
        "id": row.id,
        "student_id": row.student_id,
        "student_name": f"{row.student.first_name} {row.student.surname}",
        "class_name": row.class_name,
        "date": row.class_date.isoformat(),
        "status": row.status,
    } for row in records]


@router.get("/students/{student_id}/attendance/summary")
def rolling_attendance_summary(
    student_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    student = _student_scope(db, user, student_id)
    today = date.today()
    start = today - timedelta(days=89)
    records = db.query(ClassAttendanceRecord).filter(
        ClassAttendanceRecord.student_id == student.id,
        ClassAttendanceRecord.class_date >= start,
        ClassAttendanceRecord.class_date <= today,
    ).order_by(ClassAttendanceRecord.class_date.desc()).all()
    if user.role == UserRole.lecturer:
        records = [row for row in records if _lecturer_can_see_class(user, row, student)]
    return _attendance_summary(records, start, today)


def _lecturer_can_see_class(user: User, record: ClassAttendanceRecord, student: StudentProfile) -> bool:
    try:
        _module_scope(user, record.module, student)
        return True
    except HTTPException as error:
        if error.status_code in (403, 404):
            return False
        raise


@router.post("/wellbeing/referrals", status_code=status.HTTP_201_CREATED)
def create_wellness_referral(
    data: WellnessReferralCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    if not data.student_message.strip():
        raise HTTPException(status_code=422, detail="A supportive student message is required")
    student = db.query(StudentProfile).filter(StudentProfile.id == data.student_id).first()
    if student is None:
        lms_db = LMSSessionLocal()
        try:
            student_mapping = lms_db.query(StudentMapping).filter(
                StudentMapping.student_id == data.student_id
            ).first()
            if student_mapping is not None:
                app_user = db.query(User).filter(
                    User.email == student_mapping.app_user_email.lower()
                ).first()
                student = app_user.student_profile if app_user else None
        finally:
            lms_db.close()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    if user.role == UserRole.lecturer:
        lms_db = LMSSessionLocal()
        try:
            mapping = lms_db.query(StaffMapping).filter(StaffMapping.app_user_email == user.email.lower()).first()
            if mapping is None:
                raise HTTPException(status_code=403, detail="No authorised lecturer mapping is configured")
            module_ids = [item.module_id for item in lms_db.query(LmsModule).filter(LmsModule.lecturer_id == mapping.lecturer_id).all()]
            student_mapping = lms_db.query(StudentMapping).filter(StudentMapping.app_user_email == student.user.email.lower()).first()
            if student_mapping is None or not lms_db.query(ModuleEnrolment).filter(
                ModuleEnrolment.student_id == student_mapping.student_id,
                ModuleEnrolment.module_id.in_(module_ids),
            ).first():
                raise HTTPException(status_code=403, detail="Student is outside your authorised teaching scope")
        finally:
            lms_db.close()
    elif user.role == UserRole.advisor:
        lms_db = LMSSessionLocal()
        try:
            mapping = lms_db.query(StudentMapping).filter(
                StudentMapping.app_user_email == student.user.email.lower()
            ).first()
            if mapping is None or not lms_db.query(LmsReferral).filter(
                LmsReferral.student_id == mapping.student_id,
                (LmsReferral.advisor_user_id == user.id) | (LmsReferral.advisor_user_id.is_(None)),
            ).first():
                raise HTTPException(status_code=404, detail="Student has no support case in your authorised scope")
        finally:
            lms_db.close()
    referral = WellnessReferral(
        student_id=student.id, created_by=user.id, student_message=data.student_message.strip()
    )
    db.add(referral)
    _audit(db, user, "WELLNESS_REFERRAL_CREATED")
    db.commit()
    db.refresh(referral)
    return {"id": referral.id, "status": referral.status, "created_at": referral.created_at.isoformat()}


@router.get("/wellbeing/referrals/mine")
def my_wellness_referrals(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    if user.student_profile is None:
        raise HTTPException(status_code=404, detail="No student profile is linked to this account")
    rows = db.query(WellnessReferral).filter(
        WellnessReferral.student_id == user.student_profile.id
    ).order_by(WellnessReferral.created_at.desc()).all()
    return [{"id": row.id, "status": row.status, "student_message": row.student_message, "created_at": row.created_at.isoformat()} for row in rows]


@router.post("/wellbeing/slots", status_code=status.HTTP_201_CREATED)
def create_wellness_slot(
    data: AppointmentSlotCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    if not data.location.strip():
        raise HTTPException(status_code=422, detail="An appointment location is required")
    if data.starts_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="Appointment slot times must include a timezone")
    if data.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Appointment slots must be in the future")
    slot = WellnessAppointmentSlot(
        starts_at=data.starts_at, duration_minutes=data.duration_minutes,
        location=data.location.strip(), created_by=user.id,
    )
    db.add(slot)
    _audit(db, user, "WELLNESS_SLOT_CREATED")
    db.commit()
    db.refresh(slot)
    return {"id": slot.id, "starts_at": _utc_iso(slot.starts_at), "duration_minutes": slot.duration_minutes, "location": slot.location}


@router.get("/wellbeing/slots/manage")
def manage_wellness_slots(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    slots = db.query(WellnessAppointmentSlot).order_by(WellnessAppointmentSlot.starts_at.desc()).limit(500).all()
    booked = {
        row.slot_id for row in db.query(WellnessAppointment.slot_id).filter(
            WellnessAppointment.status.in_(("confirmed", "follow_up"))
        ).all()
    }
    return [{
        "id": slot.id,
        "starts_at": _utc_iso(slot.starts_at),
        "duration_minutes": slot.duration_minutes,
        "location": slot.location,
        "active": slot.active,
        "booked": slot.id in booked,
    } for slot in slots]


@router.patch("/wellbeing/slots/{slot_id}")
def update_wellness_slot(
    slot_id: str,
    data: AppointmentSlotUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    slot = db.query(WellnessAppointmentSlot).filter(WellnessAppointmentSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Appointment slot not found")
    if not data.active and db.query(WellnessAppointment.id).filter(
        WellnessAppointment.slot_id == slot.id,
        WellnessAppointment.status.in_(("confirmed", "follow_up")),
    ).first():
        raise HTTPException(status_code=409, detail="Cancel or complete the booking before deactivating this slot")
    slot.active = data.active
    _audit(db, user, "WELLNESS_SLOT_UPDATED")
    db.commit()
    return {"id": slot.id, "active": slot.active}


@router.get("/wellbeing/slots")
def available_wellness_slots(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    student = user.student_profile
    if student is None or not db.query(WellnessReferral.id).filter(
        WellnessReferral.student_id == student.id, WellnessReferral.status == "active"
    ).first():
        raise HTTPException(status_code=403, detail="An active support recommendation is required to view booking slots")
    booked = select(WellnessAppointment.slot_id).where(
        WellnessAppointment.status.in_(("confirmed", "follow_up"))
    )
    slots = db.query(WellnessAppointmentSlot).filter(
        WellnessAppointmentSlot.active.is_(True),
        WellnessAppointmentSlot.starts_at > datetime.now(timezone.utc),
        ~WellnessAppointmentSlot.id.in_(booked),
    ).order_by(WellnessAppointmentSlot.starts_at).all()
    return [{"id": slot.id, "starts_at": _utc_iso(slot.starts_at), "duration_minutes": slot.duration_minutes, "location": slot.location} for slot in slots]


@router.post("/wellbeing/appointments", status_code=status.HTTP_201_CREATED)
def book_wellness_appointment(
    data: AppointmentBookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    student = user.student_profile
    referral = db.query(WellnessReferral).filter(
        WellnessReferral.id == data.referral_id, WellnessReferral.student_id == student.id if student else False,
        WellnessReferral.status == "active",
    ).first()
    if referral is None:
        raise HTTPException(status_code=403, detail="An active support recommendation is required to book")
    slot = db.query(WellnessAppointmentSlot).filter(
        WellnessAppointmentSlot.id == data.slot_id, WellnessAppointmentSlot.active.is_(True),
        WellnessAppointmentSlot.starts_at > datetime.now(timezone.utc),
    ).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Appointment slot is unavailable")
    appointment = WellnessAppointment(referral_id=referral.id, slot_id=slot.id, student_id=student.id)
    db.add(appointment)
    _audit(db, user, "WELLNESS_APPOINTMENT_BOOKED")
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Appointment slot is no longer available") from error
    db.refresh(appointment)
    return {"id": appointment.id, "status": appointment.status, "starts_at": _utc_iso(slot.starts_at), "location": slot.location}


@router.get("/wellbeing/appointments")
def list_wellness_appointments(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.student, UserRole.advisor, UserRole.admin)),
):
    query = db.query(WellnessAppointment).join(WellnessAppointmentSlot).order_by(WellnessAppointmentSlot.starts_at)
    if user.role == UserRole.advisor:
        query = query.join(WellnessReferral).filter(
            (WellnessReferral.assigned_to == user.id) | (WellnessReferral.assigned_to.is_(None))
        )
    if user.role == UserRole.student:
        if user.student_profile is None:
            raise HTTPException(status_code=404, detail="No student profile is linked to this account")
        query = query.filter(WellnessAppointment.student_id == user.student_profile.id)
    return [{
        "id": row.id, "student_id": row.student_id if user.role != UserRole.student else None,
        "status": row.status,         "starts_at": _utc_iso(row.slot.starts_at),
        "duration_minutes": row.slot.duration_minutes, "location": row.slot.location,
        "follow_up": row.follow_up if user.role != UserRole.student else None,
    } for row in query.all()]


@router.patch("/wellbeing/appointments/{appointment_id}")
def update_wellness_appointment(
    appointment_id: str,
    data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    appointment = db.query(WellnessAppointment).filter(WellnessAppointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    _wellness_referral_scope(db, user, appointment.referral_id, assign_if_unassigned=True)
    appointment.status = data.status
    appointment.follow_up = data.follow_up
    _audit(db, user, "WELLNESS_APPOINTMENT_UPDATED")
    db.commit()
    return {"id": appointment.id, "status": appointment.status}


@router.get("/wellbeing/referrals")
def list_wellness_referrals(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    query = db.query(WellnessReferral).order_by(WellnessReferral.created_at.desc())
    if user.role == UserRole.advisor:
        query = query.filter((WellnessReferral.assigned_to == user.id) | (WellnessReferral.assigned_to.is_(None)))
    referrals = query.limit(500).all()
    return [{
        "id": row.id,
        "student_id": row.student_id,
        "student_name": f"{row.student.first_name} {row.student.surname}",
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    } for row in referrals]


@router.patch("/wellbeing/referrals/{referral_id}")
def update_wellness_referral(
    referral_id: str,
    data: WellnessReferralStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
):
    referral = db.query(WellnessReferral).filter(WellnessReferral.id == referral_id).first()
    if referral is None:
        raise HTTPException(status_code=404, detail="Wellness referral not found")
    _wellness_referral_scope(db, user, referral.id, assign_if_unassigned=True)
    referral.status = data.status
    _audit(db, user, "WELLNESS_REFERRAL_UPDATED")
    db.commit()
    return {"id": referral.id, "status": referral.status}


DEFAULT_PREFERENCES = {
    "theme": "light", "accent": "blue", "layout": "comfortable",
    "study_reminders": True, "weekly_summary": True, "reminder_frequency": "weekly",
    "text_size": "default", "dashboard_order": [],
    "preferred_study_start": "18:00", "timezone": "Africa/Johannesburg",
}


@router.get("/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    return {**DEFAULT_PREFERENCES, **(row.settings if row else {})}


@router.put("/preferences")
def save_preferences(
    data: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
    if row is None:
        row = UserPreference(user_id=user.id, settings=data.model_dump())
        db.add(row)
    else:
        row.settings = data.model_dump()
    _audit(db, user, "USER_PREFERENCES_UPDATED")
    db.commit()
    return row.settings
