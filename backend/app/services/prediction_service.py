from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.student import StudentProfile
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.mood_checkin import MoodCheckin
from app.models.risk_prediction import RiskPrediction, RiskLevel
from app.models.recommendation import Recommendation
from app.models.module import Module
from datetime import datetime, timedelta, timezone


def get_student_dashboard(db: Session, student_id: str) -> dict:
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        return {"error": "Student not found"}

    # Performance
    assessments = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id)
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    current_avg = (
        db.query(func.avg(Assessment.mark))
        .filter(Assessment.student_id == student_id)
        .scalar()
    )

    # Build monthly performance history
    performance_history = _build_monthly_performance(db, student_id)

    # Module breakdown
    module_breakdown = _build_module_breakdown(db, student_id)

    # Determine trend
    # Compare the earlier half of all graded assessments with the later half,
    # so one noisy month does not flip the trend.
    graded = [a for a in reversed(assessments) if a.mark is not None]
    trend = "stable"
    if len(graded) >= 6:
        mid = len(graded) // 2
        earlier = sum(a.mark for a in graded[:mid]) / mid
        later = sum(a.mark for a in graded[mid:]) / (len(graded) - mid)
        if later > earlier + 5:
            trend = "improving"
        elif later < earlier - 5:
            trend = "declining"

    # Attendance
    attendance_records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
        .all()
    )
    latest_attendance = attendance_records[0] if attendance_records else None
    current_att = latest_attendance.attendance_percentage if latest_attendance else None

    # Attendance trend history
    att_history = _build_attendance_history(db, student_id)

    # Previous attendance (for change calculation)
    previous_att = att_history[-2]["percentage"] if len(att_history) >= 2 else current_att

    # Determine attendance status
    if current_att is None:
        att_status = "Not recorded"
    elif current_att >= 80:
        att_status = "Good"
    elif current_att >= 60:
        att_status = "Warning"
    else:
        att_status = "At Risk"

    # Risk
    latest_risk = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.student_id == student_id)
        .order_by(RiskPrediction.created_at.desc())
        .first()
    )

    # Recommendations
    recs = (
        db.query(Recommendation)
        .filter(Recommendation.student_id == student_id)
        .order_by(Recommendation.created_at.desc())
        .limit(10)
        .all()
    )

    # Wellbeing
    latest_wellbeing = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.student_id == student_id)
        .order_by(MoodCheckin.created_at.desc())
        .first()
    )

    return {
        "student": {
            "id": student.id,
            "user_id": student.user_id,
            "student_number": student.student_number,
            "first_name": student.first_name,
            "surname": student.surname,
            "programme": student.programme,
            "year_level": student.year_level,
            "created_at": student.created_at.isoformat() if student.created_at else "",
        },
        "performance": {
            "current_average": round(float(current_avg), 1) if current_avg is not None else None,
            "trend": trend,
            "history": performance_history,
            "module_breakdown": module_breakdown,
        },
        "attendance": {
            "current": current_att,
            "previous": previous_att,
            "change": round(current_att - previous_att, 1) if current_att is not None and previous_att is not None else None,
            "status": att_status,
            "history": att_history,
        },
        "risk": _format_risk(latest_risk),
        "recommendations": [_format_rec(r) for r in recs],
        "wellbeing": {
            "mood_score": latest_wellbeing.mood_score if latest_wellbeing else None,
            "stress_level": latest_wellbeing.stress_level if latest_wellbeing else None,
            "last_checkin": latest_wellbeing.created_at.isoformat() if latest_wellbeing else "",
        },
    }


def _build_monthly_performance(db: Session, student_id: str) -> list[dict]:
    """Build monthly average performance from assessments."""
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    results = (
        db.query(
            extract("month", Assessment.assessment_date).label("month"),
            func.avg(Assessment.mark).label("avg"),
        )
        .filter(Assessment.student_id == student_id)
        .group_by(extract("month", Assessment.assessment_date))
        .order_by("month")
        .all()
    )
    return [
        {"month": month_names.get(int(r.month), f"M{r.month}"), "average": round(float(r.avg), 1)}
        for r in results
    ]


def _build_module_breakdown(db: Session, student_id: str) -> list[dict]:
    """Build module-level average marks."""
    results = (
        db.query(
            Module.module_name,
            func.avg(Assessment.mark).label("avg"),
        )
        .join(Assessment, Assessment.module_id == Module.id)
        .filter(Assessment.student_id == student_id)
        .group_by(Module.module_name)
        .all()
    )
    return [{"module": r.module_name, "mark": round(float(r.avg), 1)} for r in results]


def _build_attendance_history(db: Session, student_id: str) -> list[dict]:
    """Build monthly attendance history."""
    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }
    results = (
        db.query(
            extract("month", Attendance.date).label("month"),
            func.avg(Attendance.attendance_percentage).label("pct"),
        )
        .filter(Attendance.student_id == student_id)
        .group_by(extract("month", Attendance.date))
        .order_by("month")
        .all()
    )
    return [
        {"month": month_names.get(int(r.month), f"M{r.month}"), "percentage": round(float(r.pct), 1)}
        for r in results
    ]


def _format_risk(risk: Optional[RiskPrediction]) -> dict:
    if not risk:
        return {
            "risk_level": "LOW",
            "risk_score": 0,
            "explanation": "No risk assessment has been generated.",
            "factors": [],
            "model_version": "not_generated",
            "created_at": "",
        }
    factors = [{"factor": "Data-driven risk assessment", "impact": "High", "direction": "increase"}]
    if risk.model_version == "extended_data_import_v1":
        prefix = "Primary recorded risk factor: "
        factor = risk.explanation.removeprefix(prefix).split(".", 1)[0]
        factors = [{"factor": factor, "impact": "Recorded", "direction": "increase"}]
    return {
        "id": risk.id,
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level.value,
        "explanation": risk.explanation,
        "factors": factors,
        "model_version": risk.model_version,
        "created_at": risk.created_at.isoformat() if risk.created_at else "",
    }


def _format_rec(rec: Recommendation) -> dict:
    return {
        "id": rec.id,
        "category": rec.category,
        "message": rec.message,
        "priority": rec.priority,
        "status": rec.status,
        "created_at": rec.created_at.isoformat() if rec.created_at else "",
    }
