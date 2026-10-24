from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from app.models.recommendation import Recommendation
from app.models.student import StudentProfile
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.risk_prediction import RiskPrediction

# Try to import the ML recommendation engine
try:
    import sys
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
    from ml.predictions.recommendation_engine import generate_recommendations as ml_generate_recommendations
    ml_engine_available = True
except Exception:
    ml_engine_available = False


def generate_recommendations(db: Session, student_id: str, risk_level: str) -> list[Recommendation]:
    """Generate rule-based recommendations based on student data."""

    # Build feature dict for ML engine
    avg_mark = (
        db.query(func.avg(Assessment.mark))
        .filter(Assessment.student_id == student_id)
        .scalar()
    ) or 70

    latest_att = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
        .first()
    )
    att_pct = latest_att.attendance_percentage if latest_att else 85

    # Count failed modules
    failed_count = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id, Assessment.mark < 50)
        .count()
    )

    features = {
        "attendance_percentage": att_pct,
        "academic_average": avg_mark,
        "study_hours_weekly": 12.0,
        "stress_average": 5,
        "mood_average": 5,
        "failed_module_count": failed_count,
        "lms_activity_score": avg_mark * 0.85 + 5,
    }

    recs = []

    # Try ML engine first
    if ml_engine_available:
        try:
            ml_recs = ml_generate_recommendations(features, risk_level)
            for rec in ml_recs:
                r = _make_rec(db, student_id, rec["category"], rec["message"], rec["priority"])
                recs.append(r)
        except Exception:
            pass  # fall through to rule-based

    # If no ML recs or ML unavailable, use rule-based fallback
    if not recs:
        # Check attendance
        if att_pct < 70:
            recs.append(
                _make_rec(
                    db, student_id, "attendance",
                    "Schedule a meeting with your lecturer and improve attendance to stay on track.",
                    "high"
                )
            )

        # Check assessments
        if avg_mark < 50:
            recs.append(
                _make_rec(
                    db, student_id, "academic",
                    "Attend additional academic support sessions and review course materials.",
                    "high"
                )
            )

        # Risk-based recommendations
        if risk_level in ("HIGH", "MEDIUM"):
            recs.append(
                _make_rec(
                    db, student_id, "study",
                    "Increase weekly study hours by 2 hours and schedule regular revision sessions.",
                    "medium",
                )
            )
            recs.append(
                _make_rec(
                    db, student_id, "wellbeing",
                    "Consider accessing student wellbeing support services for guidance.",
                    "medium",
                )
            )

    return recs


def _make_rec(
    db: Session, student_id: str, category: str, message: str, priority: str
) -> Recommendation:
    rec = Recommendation(
        student_id=student_id,
        category=category,
        message=message,
        priority=priority,
        status="new",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
