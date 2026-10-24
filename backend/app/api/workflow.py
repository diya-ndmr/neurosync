from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.middleware.security import require_role
from app.models.user import User, UserRole
from app.schemas.workflow_schema import (
    AdvisorNoteCreate,
    CustomStrategyCreate,
    EmailApproval,
    EmailDraftCreate,
    InterventionUpdate,
    MeetingCreate,
    MeetingUpdate,
    RecommendationDecision,
    ReferralCreate,
    ReferralStatusUpdate,
)
from lms.database import LMSSessionLocal
from lms.models import (
    AdvisorNote,
    DatasetSourceRow,
    Intervention,
    MockEmail,
    Module,
    ModuleEnrolment,
    Referral,
    StaffMapping,
    Student,
    StudentMeeting,
    StudentResponse,
    WorkflowEvent,
)
from lms.workflow_service import (
    STRATEGIES,
    _intervention_json,
    _referral_json,
    build_assessment_intelligence,
    build_intervention_comparison,
    build_student_review,
    capture_academic_snapshot,
    draft_supportive_email,
    record_event,
    recommend_strategies,
)

router = APIRouter(prefix="/api/workflow", tags=["Student Support Workflow"])


def _get_lms_db():
    db = LMSSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _lecturer_id(db: Session, user: User) -> str:
    mapping = db.query(StaffMapping).filter(StaffMapping.app_user_email == user.email.lower()).first()
    if mapping is None:
        raise HTTPException(status_code=403, detail="No authorised LMS lecturer mapping is configured")
    return mapping.lecturer_id


def _lecturer_module_ids(db: Session, lecturer_id: str) -> set[str]:
    return {
        row.module_id
        for row in db.query(Module.module_id).filter(Module.lecturer_id == lecturer_id).all()
    }


def _lecturer_can_view(db: Session, user: User, student_id: str, module_id: Optional[str] = None) -> bool:
    lecturer_id = _lecturer_id(db, user)
    module_ids = _lecturer_module_ids(db, lecturer_id)
    query = db.query(ModuleEnrolment).filter(
        ModuleEnrolment.student_id == student_id,
        ModuleEnrolment.module_id.in_(module_ids),
    )
    if module_id is not None:
        query = query.filter(ModuleEnrolment.module_id == module_id)
    return query.first() is not None


def _require_student_scope(db: Session, user: User, student_id: str, module_id: Optional[str] = None) -> None:
    if user.role == UserRole.admin:
        return
    if user.role == UserRole.lecturer:
        if not _lecturer_can_view(db, user, student_id, module_id):
            raise HTTPException(status_code=404, detail="Student not found in your authorised teaching scope")
        return
    if user.role == UserRole.advisor:
        query = db.query(Referral).filter(Referral.student_id == student_id)
        query = query.filter((Referral.advisor_user_id == user.id) | (Referral.advisor_user_id.is_(None)))
        if query.first() is None:
            raise HTTPException(status_code=404, detail="Student has no referral in your authorised case scope")
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _require_referral(db: Session, user: User, referral_id: str) -> Referral:
    referral = db.query(Referral).filter(Referral.referral_id == referral_id).first()
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral not found")
    if user.role == UserRole.admin:
        return referral
    if user.role == UserRole.advisor:
        if referral.advisor_user_id not in (None, user.id):
            raise HTTPException(status_code=404, detail="Referral not found")
        return referral
    if user.role == UserRole.lecturer:
        if referral.lecturer_id != _lecturer_id(db, user):
            raise HTTPException(status_code=404, detail="Referral not found")
        return referral
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def _require_advisor_owner(user: User, referral: Referral) -> None:
    if user.role != UserRole.advisor:
        raise HTTPException(status_code=403, detail="Advisor role required")
    if referral.advisor_user_id not in (None, user.id):
        raise HTTPException(status_code=404, detail="Referral not found")
    if referral.advisor_user_id is None:
        referral.advisor_user_id = user.id
        referral.status = "ASSIGNED"


def _write_event(db: Session, student_id: str, user: User, event_type: str, summary: str,
                 referral_id: Optional[str] = None, visibility: str = "SHARED") -> None:
    record_event(db, student_id, user.id, event_type, summary, referral_id, visibility)


@router.get("/lecturer/modules")
def lecturer_modules(
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    if user.role == UserRole.admin:
        modules = db.query(Module).all()
    else:
        modules = db.query(Module).filter(Module.lecturer_id == _lecturer_id(db, user)).all()
    return [{"module_id": module.module_id, "module_code": module.module_code, "module_name": module.module_name} for module in modules]


@router.get("/lecturer/modules/{module_id}/assessment-intelligence")
def lecturer_module_assessment_intelligence(
    module_id: str,
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    if user.role == UserRole.admin:
        module_exists = db.query(Module.module_id).filter(Module.module_id == module_id).first()
    else:
        module_exists = db.query(Module.module_id).filter(
            Module.module_id == module_id,
            Module.lecturer_id == _lecturer_id(db, user),
        ).first()
    if module_exists is None:
        raise HTTPException(status_code=404, detail="Module not found in your authorised teaching scope")
    return build_assessment_intelligence(db, module_id)


@router.get("/lecturer/students")
def lecturer_students(
    module_id: Optional[str] = Query(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    if user.role == UserRole.admin:
        module_ids = {row.module_id for row in db.query(Module.module_id).all()}
    else:
        module_ids = _lecturer_module_ids(db, _lecturer_id(db, user))
    if module_id:
        if module_id not in module_ids:
            raise HTTPException(status_code=404, detail="Module not found in your authorised teaching scope")
        module_ids = {module_id}
    if not module_ids:
        return {"items": []}
    from sqlalchemy import func
    from lms.models import AssessmentResult, MonthlyAttendanceSummary, Submission
    student_ids = [row[0] for row in db.query(ModuleEnrolment.student_id).filter(ModuleEnrolment.module_id.in_(module_ids)).distinct().all()]
    mark_rows = dict(db.query(AssessmentResult.student_id, func.avg(AssessmentResult.percentage)).filter(AssessmentResult.student_id.in_(student_ids)).group_by(AssessmentResult.student_id).all())
    attendance_rows = dict(db.query(MonthlyAttendanceSummary.student_id, func.avg(MonthlyAttendanceSummary.attendance_percentage)).filter(MonthlyAttendanceSummary.student_id.in_(student_ids)).group_by(MonthlyAttendanceSummary.student_id).all())
    missing_rows = dict(db.query(Submission.student_id, func.sum(Submission.status == 'MISSING')).filter(Submission.student_id.in_(student_ids)).group_by(Submission.student_id).all())
    items = []
    for student in db.query(Student).filter(Student.student_id.in_(student_ids)).all():
        average = round(float(mark_rows.get(student.student_id) or 0), 1)
        attendance = round(float(attendance_rows.get(student.student_id) or 0), 1)
        missing = int(missing_rows.get(student.student_id) or 0)
        level = 'HIGH' if average <= 50 else 'MEDIUM' if average < 75 else 'LOW'
        modules = db.query(Module).join(ModuleEnrolment, ModuleEnrolment.module_id == Module.module_id).filter(ModuleEnrolment.student_id == student.student_id, Module.module_id.in_(module_ids)).all()
        items.append({
            "student_id": student.student_id,
            "name": f"{student.first_name} {student.surname}",
            "programme": student.programme.programme_name if student.programme else student.programme_id,
            "year_of_study": student.year_of_study,
            "institutional_email": student.institutional_email,
            "enrolment_status": student.enrolment_status,
            "modules": [{"module_id": item.module_id, "module_code": item.module_code, "module_name": item.module_name} for item in modules],
            "metrics": {"academic_average": average, "attendance": attendance, "attendance_30d": attendance, "attendance_7d": attendance, "attendance_change_30d": 0, "submission_rate": 0 if missing else 100, "late_submissions": 0, "missing_submissions": missing, "quiz_average": 0, "quiz_completion_rate": 0, "engagement_score": 0, "assessment_trend": 'stable'},
            "risk": {"risk_level": level, "risk_score": average, "evidence": [f"Academic average is {average}%.", f"{missing} missing submission(s) recorded."], "trajectory": 'stable', "trajectory_evidence": []},
        })
    items.sort(key=lambda item: (-item["risk"]["risk_score"], item["student_id"]))
    return {"items": items}


@router.get("/weekly-briefing")
def weekly_intelligence_briefing(
    user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    follow_up_deadline = date.today() + timedelta(days=7)

    if user.role == UserRole.lecturer:
        lecturer_id = _lecturer_id(db, user)
        recent_referrals = (
            db.query(Referral)
            .filter(Referral.lecturer_id == lecturer_id, Referral.created_at >= week_ago)
            .order_by(Referral.created_at.desc())
            .limit(50)
            .all()
        )
        items = [{
            "type": "REFERRAL_CREATED",
            "referral_id": row.referral_id,
            "student_id": row.student_id,
            "module_id": row.module_id,
            "risk_level": row.risk_level,
            "risk_score": row.risk_score,
            "urgency": row.urgency,
            "status": row.status,
            "recorded_at": row.created_at.isoformat(),
        } for row in recent_referrals]
        return {
            "role": user.role.value,
            "period_days": 7,
            "summary": {"new_referrals": len(items), "priority_referrals": sum(item["urgency"] == "PRIORITY" for item in items)},
            "items": items,
            "data_basis": "Referrals recorded in the last 7 days within your teaching scope.",
        }

    if user.role == UserRole.advisor:
        referrals = (
            db.query(Referral)
            .filter((Referral.advisor_user_id == user.id) | (Referral.advisor_user_id.is_(None)))
            .order_by(Referral.created_at.desc())
            .all()
        )
        new_referrals = [row for row in referrals if row.created_at >= week_ago]
        follow_ups = (
            db.query(Intervention)
            .filter(
                Intervention.advisor_user_id == user.id,
                Intervention.follow_up_date <= follow_up_deadline,
                Intervention.status.in_(["PLANNED", "ACTIVE", "FOLLOW_UP"]),
            )
            .order_by(Intervention.follow_up_date.asc())
            .limit(50)
            .all()
        )
        items = [{
            "type": "NEW_REFERRAL",
            "referral_id": row.referral_id,
            "student_id": row.student_id,
            "risk_level": row.risk_level,
            "urgency": row.urgency,
            "status": row.status,
            "recorded_at": row.created_at.isoformat(),
        } for row in new_referrals]
        items.extend({
            "type": "FOLLOW_UP_DUE",
            "referral_id": row.referral_id,
            "student_id": row.student_id,
            "strategy": row.strategy,
            "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
            "status": row.status,
        } for row in follow_ups)
        return {
            "role": user.role.value,
            "period_days": 7,
            "summary": {"new_referrals": len(new_referrals), "follow_ups_due": len(follow_ups)},
            "items": items,
            "data_basis": "New visible referrals from the last 7 days and your assigned follow-ups due within 7 days.",
        }

    recent_referrals = db.query(Referral).filter(Referral.created_at >= week_ago).all()
    return {
        "role": user.role.value,
        "period_days": 7,
        "summary": {
            "new_referrals": len(recent_referrals),
            "priority_referrals": sum(row.urgency == "PRIORITY" for row in recent_referrals),
            "high_risk_referrals": sum(row.risk_level == "HIGH" for row in recent_referrals),
        },
        "items": [],
        "data_basis": "Aggregated referrals recorded in the last 7 days; student-level details are withheld.",
    }


@router.get("/students/{student_id}/review")
def student_review(
    student_id: str,
    module_id: Optional[str] = Query(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    _require_student_scope(db, user, student_id, module_id)
    if user.role == UserRole.lecturer:
        _write_event(db, student_id, user, "LECTURER_VIEWED_STUDENT", "Lecturer reviewed the LMS academic profile.")
        _write_event(db, student_id, user, "LECTURER_VIEWED_ATTENDANCE", "Lecturer viewed attendance records.")
        _write_event(db, student_id, user, "LECTURER_VIEWED_SUBMISSIONS", "Lecturer viewed submission records.")
        db.commit()
    review = build_student_review(db, student_id)
    if user.role == UserRole.lecturer:
        lecturer_id = _lecturer_id(db, user)
        review["referrals"] = [item for item in review["referrals"] if item["lecturer_id"] == lecturer_id]
    # Follow-up evidence: compare the recorded pre-intervention baseline with the
    # current indicators for the most recent referral this user may see.
    visible_referrals = review.get("referrals") or []
    latest_referral = (
        db.query(Referral).filter(Referral.referral_id == visible_referrals[0]["referral_id"]).first()
        if visible_referrals else None
    )
    review["intervention_comparison"] = (
        build_intervention_comparison(db, latest_referral, review) if latest_referral else None
    )
    return review


@router.post("/referrals", status_code=status.HTTP_201_CREATED)
def create_referral(
    data: ReferralCreate,
    user: User = Depends(require_role(UserRole.lecturer)),
    db: Session = Depends(_get_lms_db),
):
    student = db.query(Student).filter(Student.student_id == data.student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    lecturer_id = _lecturer_id(db, user)
    module_id = data.module_id
    if user.role == UserRole.lecturer:
        if module_id is None or not _lecturer_can_view(db, user, data.student_id, module_id):
            raise HTTPException(status_code=404, detail="Student or module not found in your authorised teaching scope")
    elif module_id and not db.query(Module).filter(Module.module_id == module_id).first():
        raise HTTPException(status_code=404, detail="Module not found")
    review = build_student_review(db, data.student_id)
    referral = Referral(
        student_id=data.student_id,
        lecturer_id=lecturer_id,
        module_id=module_id,
        risk_level=review["risk"]["risk_level"],
        risk_score=review["risk"]["risk_score"],
        reason=data.reason,
        lecturer_notes=data.lecturer_notes,
        urgency=data.urgency,
    )
    db.add(referral)
    db.flush()
    _write_event(db, data.student_id, user, "STUDENT_REFERRED", "Lecturer referred student for academic advisor review.", referral.referral_id)
    capture_academic_snapshot(db, referral, review, captured_by=user.id)
    _write_event(db, data.student_id, user, "ACADEMIC_SNAPSHOT_RECORDED", "Baseline academic indicators recorded for follow-up comparison.", referral.referral_id)
    db.commit()
    db.refresh(referral)
    return _referral_json(referral)


@router.post("/students/{student_id}/monitor")
def continue_monitoring(
    student_id: str,
    module_id: str = Query(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"),
    user: User = Depends(require_role(UserRole.lecturer)),
    db: Session = Depends(_get_lms_db),
):
    if not _lecturer_can_view(db, user, student_id, module_id):
        raise HTTPException(status_code=404, detail="Student or module not found in your authorised teaching scope")
    _write_event(db, student_id, user, "LECTURER_CONTINUE_MONITORING", "Lecturer chose to continue monitoring the student's academic indicators.")
    db.commit()
    return {"student_id": student_id, "status": "MONITORING", "recorded": True}


@router.get("/advisor/dashboard")
def advisor_dashboard(
    include_closed: bool = Query(default=False),
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    query = db.query(Referral)
    if user.role == UserRole.advisor:
        query = query.filter((Referral.advisor_user_id == user.id) | (Referral.advisor_user_id.is_(None)))
    if not include_closed:
        query = query.filter(Referral.status != "CLOSED")
    referrals = query.order_by(Referral.created_at.desc()).all()
    buckets = {
        "new_referrals": sum(row.status == "REFERRED" for row in referrals),
        "assigned_students": sum(row.advisor_user_id == user.id for row in referrals),
        "students_to_contact": sum(row.status in {"ASSIGNED", "UNDER_REVIEW"} for row in referrals),
        "awaiting_response": sum(row.status == "AWAITING_RESPONSE" for row in referrals),
        "meetings_scheduled": sum(row.status == "MEETING_SCHEDULED" for row in referrals),
        "active_interventions": sum(row.status == "INTERVENTION_ACTIVE" for row in referrals),
        "follow_ups_due": db.query(Intervention).filter(Intervention.advisor_user_id == user.id, Intervention.status == "FOLLOW_UP").count(),
        "resolved_cases": sum(row.status in {"RESOLVED", "CLOSED"} for row in referrals),
    }
    items = []
    for row in referrals:
        student = db.query(Student).filter(Student.student_id == row.student_id).first()
        item = _referral_json(row)
        item["student_name"] = f"{student.first_name} {student.surname}" if student else row.student_id
        items.append(item)
    return {
        "summary": buckets,
        "items": items,
        "imported_demo_dataset": _contact_demo_dataset(db),
    }


def _contact_demo_dataset(db: Session) -> Optional[dict[str, Any]]:
    source_names = {
        "students_100_with_contacts.csv",
        "neurosync_all_100_students_combined.csv",
        "advisor_referrals.csv",
        "advisor_interventions.csv",
        "advisor_actions.csv",
        "student_support_requests.csv",
    }
    rows = (
        db.query(DatasetSourceRow)
        .filter(
            DatasetSourceRow.source_name.in_(source_names),
            DatasetSourceRow.source_row_id.like("contact-demo:%"),
        )
        .order_by(DatasetSourceRow.source_name, DatasetSourceRow.row_number)
        .all()
    )
    if not rows:
        return None

    records: dict[str, list[dict[str, str]]] = {name: [] for name in source_names}
    for row in rows:
        records[row.source_name].append(json.loads(row.payload))

    students = records["students_100_with_contacts.csv"]
    return {
        "label": "Separate synthetic CSV dataset (not merged into LMS records)",
        "counts": {
            "students": len(students),
            "combined_summaries": len(records["neurosync_all_100_students_combined.csv"]),
            "referrals": len(records["advisor_referrals.csv"]),
            "interventions": len(records["advisor_interventions.csv"]),
            "actions": len(records["advisor_actions.csv"]),
            "support_requests": len(records["student_support_requests.csv"]),
        },
        "students": [{
            "student_id": row["student_id"],
            "name": row.get("student_name") or f"{row['first_name']} {row['surname']}",
            "faculty": row["faculty"],
            "risk_level": row["risk_level"].upper(),
            "attendance_percent": row["attendance_percent"],
            "average_mark": row["average_mark"],
            "last_lms_login": row["last_lms_login"],
            "assigned_advisor": row["assigned_advisor"],
            "email": row.get("email", ""),
            "phone_number": row.get("phone_number", ""),
        } for row in students],
        "referrals": [{
            "student_id": row["student_id"],
            "referral_id": row["referral_id"],
            "advisor_id": row["advisor_id"],
            "risk_level": row["risk_level"].upper(),
            "reason": row["reason"],
            "urgency": row["urgency"],
            "status": row["status"],
            "created_date": row["created_date"],
            "next_follow_up": row["next_follow_up"],
        } for row in records["advisor_referrals.csv"]],
        "interventions": [{
            "student_id": row["student_id"],
            "intervention_id": row["intervention_id"],
            "referral_id": row["referral_id"],
            "strategy": row["support_strategy"],
            "start_date": row["start_date"],
            "review_date": row["review_date"],
            "status": row["status"],
            "follow_up_due": row["follow_up_due"],
        } for row in records["advisor_interventions.csv"]],
        "actions": [{
            "student_id": row["student_id"],
            "action_id": row["action_id"],
            "referral_id": row["referral_id"],
            "action_type": row["action_type"],
            "due_date": row["due_date"],
            "status": row["status"],
            "priority": row["priority"],
        } for row in records["advisor_actions.csv"]],
        "support_requests": [{
            "student_id": row["student_id"],
            "request_id": row["request_id"],
            "request_type": row["request_type"],
            "submitted_date": row["submitted_date"],
            "status": row["status"],
            "assigned_advisor": row["assigned_advisor"],
        } for row in records["student_support_requests.csv"]],
    }


@router.get("/advisor/referrals/{referral_id}")
def advisor_referral_detail(
    referral_id: str,
    user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    if user.role == UserRole.advisor:
        _require_advisor_owner(user, referral)
        _write_event(db, referral.student_id, user, "ADVISOR_VIEWED_REFERRAL", "Advisor reviewed a student referral.", referral.referral_id)
        db.commit()
    review = build_student_review(db, referral.student_id)
    events_query = db.query(WorkflowEvent).filter(WorkflowEvent.referral_id == referral.referral_id, WorkflowEvent.visibility == "SHARED")
    events = events_query.order_by(WorkflowEvent.occurred_at.asc()).all()
    interventions = db.query(Intervention).filter(Intervention.referral_id == referral.referral_id).all()
    result: dict[str, Any] = {
        "referral": _referral_json(referral),
        "review": review,
        "recommendations": recommend_strategies(review) if user.role in {UserRole.advisor, UserRole.admin} else [],
        "interventions": [_intervention_json(item) for item in interventions],
        "timeline": [{"event_type": event.event_type, "summary": event.summary, "occurred_at": event.occurred_at.isoformat()} for event in events],
        "comparison": build_intervention_comparison(db, referral, review),
    }
    if user.role in {UserRole.advisor, UserRole.admin}:
        result["advisor_notes"] = [
            {"note_id": note.note_id, "note": note.note, "created_at": note.created_at.isoformat()}
            for note in db.query(AdvisorNote).filter(AdvisorNote.referral_id == referral.referral_id).order_by(AdvisorNote.created_at.asc()).all()
        ]
        result["communications"] = [
            {"message_id": row.message_id, "subject": row.subject, "delivery_status": row.delivery_status,
             "sent_at": row.sent_at.isoformat() if row.sent_at else None, "created_at": row.created_at.isoformat(), "body": row.body}
            for row in db.query(MockEmail).filter(MockEmail.referral_id == referral.referral_id).order_by(MockEmail.created_at.asc()).all()
        ]
        result["communications"].extend([
            {"message_id": row.response_id, "subject": f"Synthetic student {row.response_type.lower()}",
             "delivery_status": row.response_type, "sent_at": row.occurred_at.isoformat(),
             "created_at": row.occurred_at.isoformat(), "body": row.response_text or "No response received.", "synthetic": row.synthetic}
            for row in db.query(StudentResponse).filter(StudentResponse.referral_id == referral.referral_id).order_by(StudentResponse.occurred_at.asc()).all()
        ])
        result["meetings"] = [
            {"meeting_id": row.meeting_id, "meeting_at": row.meeting_at.isoformat(), "purpose": row.purpose, "status": row.status, "advisor_notes": row.advisor_notes}
            for row in db.query(StudentMeeting).filter(StudentMeeting.referral_id == referral.referral_id).order_by(StudentMeeting.meeting_at.asc()).all()
        ]
    return result


@router.get("/advisor/referrals/{referral_id}/comparison")
def referral_comparison(
    referral_id: str,
    user: User = Depends(require_role(UserRole.lecturer, UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    """Before-intervention vs current academic indicators for the follow-up stage."""
    referral = _require_referral(db, user, referral_id)
    if user.role == UserRole.advisor:
        _require_advisor_owner(user, referral)
    comparison = build_intervention_comparison(db, referral)
    if comparison is None:
        raise HTTPException(status_code=404, detail="No academic baseline was recorded for this referral")
    return comparison


@router.post("/advisor/referrals/{referral_id}/assign")
def assign_referral(
    referral_id: str,
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    if user.role == UserRole.advisor:
        _require_advisor_owner(user, referral)
    else:
        referral.advisor_user_id = user.id
    referral.status = "ASSIGNED"
    referral.updated_at = datetime.now(timezone.utc)
    _write_event(db, referral.student_id, user, "ADVISOR_ASSIGNED", "Referral assigned to an authorised academic advisor.", referral.referral_id)
    db.commit()
    return _referral_json(referral)


@router.patch("/advisor/referrals/{referral_id}/status")
def update_referral_status(
    referral_id: str,
    data: ReferralStatusUpdate,
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    if user.role == UserRole.advisor:
        _require_advisor_owner(user, referral)
    referral.status = data.status
    referral.updated_at = datetime.now(timezone.utc)
    event_type = "CASE_RESOLVED" if data.status == "RESOLVED" else "INTERVENTION_UPDATED"
    _write_event(db, referral.student_id, user, event_type, f"Referral status updated to {data.status}.", referral.referral_id)
    db.commit()
    return _referral_json(referral)


@router.get("/advisor/referrals/{referral_id}/strategies")
def strategy_recommendations(
    referral_id: str,
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    if user.role == UserRole.advisor:
        _require_advisor_owner(user, referral)
    review = build_student_review(db, referral.student_id)
    suggestions = recommend_strategies(review)
    _write_event(db, referral.student_id, user, "AI_STRATEGY_GENERATED", "Academic-indicator-based strategy suggestions generated.", referral.referral_id)
    db.commit()
    return {"suggestions": suggestions, "strategy_library": list(STRATEGIES), "human_decision_required": True}


@router.get("/advisor/referrals/{referral_id}/email-suggestion")
def email_suggestion(
    referral_id: str,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    suggestion = draft_supportive_email(build_student_review(db, referral.student_id))
    _write_event(db, referral.student_id, user, "EMAIL_DRAFT_CREATED", "Indicator-grounded email draft suggested for advisor review.", referral.referral_id)
    db.commit()
    return {**suggestion, "requires_advisor_review": True}


@router.post("/advisor/referrals/{referral_id}/strategies/decision")
def decide_recommendation(
    referral_id: str,
    data: RecommendationDecision,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    if data.strategy not in STRATEGIES and data.decision != "DISMISS":
        raise HTTPException(status_code=422, detail="Choose a strategy from the library or create a custom strategy")
    if data.decision == "DISMISS":
        event_type = "AI_STRATEGY_REJECTED"
        summary = f"Advisor dismissed the suggested strategy: {data.strategy}."
    elif data.decision == "CHOOSE_DIFFERENT":
        event_type = "AI_STRATEGY_REJECTED"
        summary = f"Advisor declined the suggested strategy and selected: {data.strategy}."
    else:
        event_type = "AI_STRATEGY_ACCEPTED"
        summary = f"Advisor {data.decision.lower()} the strategy: {data.strategy}."
        intervention = Intervention(
            referral_id=referral.referral_id,
            student_id=referral.student_id,
            advisor_user_id=user.id,
            strategy=data.strategy,
            reason=data.reason,
            advisor_notes=data.advisor_notes,
            review_date=data.review_date,
            follow_up_date=data.follow_up_date,
            status="PLANNED",
        )
        db.add(intervention)
        db.flush()
        referral.status = "INTERVENTION_ACTIVE"
    _write_event(db, referral.student_id, user, event_type, summary, referral.referral_id)
    db.commit()
    return {"decision": data.decision, "strategy": data.strategy}


@router.post("/advisor/referrals/{referral_id}/strategies/custom", status_code=status.HTTP_201_CREATED)
def custom_strategy(
    referral_id: str,
    data: CustomStrategyCreate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    intervention = Intervention(
        referral_id=referral.referral_id,
        student_id=referral.student_id,
        advisor_user_id=user.id,
        strategy=data.strategy,
        reason=data.reason,
        advisor_notes=data.advisor_notes,
        review_date=data.review_date,
        follow_up_date=data.follow_up_date,
        status="PLANNED",
    )
    db.add(intervention)
    referral.status = "INTERVENTION_ACTIVE"
    _write_event(db, referral.student_id, user, "CUSTOM_STRATEGY_SELECTED", f"Advisor created a custom strategy: {data.strategy}.", referral.referral_id)
    db.commit()
    db.refresh(intervention)
    return _intervention_json(intervention)


@router.patch("/advisor/interventions/{intervention_id}")
def update_intervention(
    intervention_id: str,
    data: InterventionUpdate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    intervention = db.query(Intervention).filter(Intervention.intervention_id == intervention_id, Intervention.advisor_user_id == user.id).first()
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    changes = data.model_dump(exclude_unset=True)
    change_summaries = []
    field_labels = {
        "status": "status",
        "outcome": "outcome",
        "follow_up_date": "follow-up date",
        "review_date": "review date",
    }
    for key, value in changes.items():
        previous = getattr(intervention, key)
        if previous == value:
            continue
        setattr(intervention, key, value)
        if key == "advisor_notes":
            change_summaries.append("advisor notes updated")
        else:
            label = field_labels[key]
            change_summaries.append(f"{label}: {previous or 'not set'} -> {value or 'not set'}")
    if change_summaries:
        intervention.updated_at = datetime.now(timezone.utc)
    referral = db.query(Referral).filter(Referral.referral_id == intervention.referral_id).first()
    if referral:
        if intervention.status == "FOLLOW_UP":
            referral.status = "FOLLOW_UP"
        elif intervention.status == "COMPLETED":
            referral.status = "RESOLVED"
        if change_summaries:
            event_type = "FOLLOW_UP_RECORDED" if "follow_up_date" in changes else "INTERVENTION_UPDATED"
            summary = "Advisor updated intervention: " + "; ".join(change_summaries) + "."
            _write_event(db, intervention.student_id, user, event_type, summary, referral.referral_id)
    db.commit()
    return _intervention_json(intervention)


@router.get("/advisor/interventions")
def advisor_interventions(
    user: User = Depends(require_role(UserRole.advisor, UserRole.admin)),
    db: Session = Depends(_get_lms_db),
):
    query = db.query(Intervention)
    if user.role == UserRole.advisor:
        query = query.filter(Intervention.advisor_user_id == user.id)
    rows = query.order_by(Intervention.follow_up_date.asc(), Intervention.created_at.desc()).all()
    items = []
    for row in rows:
        referral = db.query(Referral).filter(Referral.referral_id == row.referral_id).first()
        student = db.query(Student).filter(Student.student_id == row.student_id).first()
        item = _intervention_json(row)
        item["student_name"] = f"{student.first_name} {student.surname}" if student else row.student_id
        item["student_id"] = row.student_id
        item["referral_status"] = referral.status if referral else "UNKNOWN"
        items.append(item)
    return {"items": items}


@router.post("/advisor/referrals/{referral_id}/notes", status_code=status.HTTP_201_CREATED)
def add_advisor_note(
    referral_id: str,
    data: AdvisorNoteCreate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    note = AdvisorNote(referral_id=referral.referral_id, student_id=referral.student_id, advisor_user_id=user.id, note=data.note)
    db.add(note)
    _write_event(db, referral.student_id, user, "ADVISOR_NOTE_ADDED", "Advisor added a protected case note.", referral.referral_id, visibility="ADVISOR_ONLY")
    db.commit()
    db.refresh(note)
    return {"note_id": note.note_id, "created_at": note.created_at.isoformat()}


@router.post("/advisor/referrals/{referral_id}/email-drafts", status_code=status.HTTP_201_CREATED)
def create_email_draft(
    referral_id: str,
    data: EmailDraftCreate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    student = db.query(Student).filter(Student.student_id == referral.student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    message = MockEmail(
        referral_id=referral.referral_id,
        student_id=referral.student_id,
        advisor_user_id=user.id,
        recipient=student.institutional_email,
        subject=data.subject,
        body=data.body,
        drafted_by_ai=data.drafted_by_ai,
        delivery_status="DRAFT",
    )
    db.add(message)
    _write_event(db, referral.student_id, user, "EMAIL_DRAFT_CREATED", "Support email draft created; approval required before mock sending.", referral.referral_id)
    db.commit()
    db.refresh(message)
    return {"message_id": message.message_id, "recipient": message.recipient, "delivery_status": message.delivery_status, "approval_required": True}


@router.post("/advisor/emails/{message_id}/approval")
def approve_mock_email(
    message_id: str,
    data: EmailApproval,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    message = db.query(MockEmail).filter(MockEmail.message_id == message_id, MockEmail.advisor_user_id == user.id).first()
    if message is None:
        raise HTTPException(status_code=404, detail="Email draft not found")
    referral = _require_referral(db, user, message.referral_id)
    _require_advisor_owner(user, referral)
    if not data.approve:
        message.delivery_status = "DRAFT"
        _write_event(db, message.student_id, user, "EMAIL_APPROVAL_DECLINED", "Advisor declined the mock email draft.", referral.referral_id)
    else:
        message.approved_by = user.id
        message.sent_at = datetime.now(timezone.utc)
        message.delivery_status = "SENT"
        referral.status = "STUDENT_CONTACTED"
        _write_event(db, message.student_id, user, "EMAIL_APPROVED", "Advisor approved the student message.", referral.referral_id)
        _write_event(db, message.student_id, user, "EMAIL_SENT", "Mock institutional email recorded as sent; no external delivery occurred.", referral.referral_id)
    db.commit()
    return {"message_id": message.message_id, "delivery_status": message.delivery_status, "external_delivery": False}


@router.post("/advisor/referrals/{referral_id}/meetings", status_code=status.HTTP_201_CREATED)
def schedule_meeting(
    referral_id: str,
    data: MeetingCreate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    meeting = StudentMeeting(referral_id=referral.referral_id, student_id=referral.student_id, advisor_user_id=user.id, meeting_at=data.meeting_at, purpose=data.purpose)
    db.add(meeting)
    referral.status = "MEETING_SCHEDULED"
    _write_event(db, referral.student_id, user, "MEETING_SCHEDULED", "Advisor scheduled a student support meeting.", referral.referral_id)
    db.commit()
    db.refresh(meeting)
    return {"meeting_id": meeting.meeting_id, "meeting_at": meeting.meeting_at.isoformat(), "status": meeting.status}


@router.patch("/advisor/meetings/{meeting_id}")
def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    meeting = db.query(StudentMeeting).filter(StudentMeeting.meeting_id == meeting_id, StudentMeeting.advisor_user_id == user.id).first()
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.status = data.status
    if data.advisor_notes is not None:
        meeting.advisor_notes = data.advisor_notes
    _write_event(db, meeting.student_id, user, data.status, "Advisor updated meeting status.", meeting.referral_id)
    db.commit()
    return {"meeting_id": meeting.meeting_id, "status": meeting.status}


@router.post("/advisor/referrals/{referral_id}/mock-response")
def record_synthetic_student_response(
    referral_id: str,
    response: str = Query(min_length=5, max_length=1200),
    status_value: str = Query(pattern="^(READ|REPLIED|MEETING_REQUESTED|NO_RESPONSE|DECLINED_SUPPORT|ACCEPTED_SUPPORT)$"),
    user: User = Depends(require_role(UserRole.advisor)),
    db: Session = Depends(_get_lms_db),
):
    referral = _require_referral(db, user, referral_id)
    _require_advisor_owner(user, referral)
    if status_value == "NO_RESPONSE":
        summary = "Synthetic demonstration: student has not responded yet."
    else:
        summary = f"Synthetic student response recorded ({status_value}); response content is retained only in the case workflow."
    if status_value in {"READ", "REPLIED"}:
        message = db.query(MockEmail).filter(MockEmail.referral_id == referral.referral_id, MockEmail.delivery_status.in_(["SENT", "DELIVERED", "READ", "REPLIED"])).order_by(MockEmail.sent_at.desc()).first()
        if message:
            message.delivery_status = status_value
    message = db.query(MockEmail).filter(MockEmail.referral_id == referral.referral_id).order_by(MockEmail.created_at.desc()).first()
    db.add(StudentResponse(
        referral_id=referral.referral_id,
        student_id=referral.student_id,
        message_id=message.message_id if message else None,
        response_type=status_value,
        response_text=None if status_value == "NO_RESPONSE" else response,
        synthetic=True,
    ))
    if status_value == "MEETING_REQUESTED":
        referral.status = "MEETING_SCHEDULED"
    elif status_value in {"READ", "REPLIED"}:
        referral.status = "AWAITING_RESPONSE" if status_value == "READ" else "UNDER_REVIEW"
    _write_event(db, referral.student_id, user, "STUDENT_RESPONSE_RECORDED", summary, referral.referral_id)
    db.commit()
    return {"referral_id": referral.referral_id, "status": status_value, "synthetic": True}
