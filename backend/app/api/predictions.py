from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.risk_prediction import RiskPrediction, RiskLevel
from app.models.student import StudentProfile
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.mood_checkin import MoodCheckin
from app.models.recommendation import Recommendation
from app.models.user import User, UserRole
from app.schemas.record_schema import PredictionRequest
from app.middleware.security import require_own_student_record, require_role
from app.services.recommendation_service import generate_recommendations
import uuid
from pathlib import Path

# Try to import the ML risk predictor
try:
    import sys
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
    from ml.predictions.predict_risk import RiskPredictor
    ml_available = True
    # Check if model files exist
    model_path = project_root / "ml" / "models" / "best_model.joblib"
    if not model_path.exists():
        ml_available = False
except Exception:
    ml_available = False

router = APIRouter(prefix="/api/predictions", tags=["Predictions"])


@router.patch("/recommendations/{recommendation_id}/complete")
def complete_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    recommendation = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if recommendation is None or recommendation.student.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    recommendation.status = "completed"
    db.commit()
    return {"id": recommendation.id, "status": recommendation.status}


def _build_feature_vector(db: Session, student_id: str) -> dict:
    """Build a feature vector for the ML model from database data."""
    avg_mark = (
        db.query(func.avg(Assessment.mark))
        .filter(Assessment.student_id == student_id)
        .scalar()
        or 70
    )

    # Latest attendance
    latest_att = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
        .first()
    )
    att_pct = latest_att.attendance_percentage if latest_att else 85

    # Attendance change (compare first and last record)
    att_records = (
        db.query(Attendance)
        .filter(Attendance.student_id == student_id)
        .order_by(Attendance.date.asc())
        .all()
    )
    att_change = 0
    if len(att_records) >= 2:
        att_change = att_records[-1].attendance_percentage - att_records[0].attendance_percentage

    # Latest wellbeing
    latest_wellbeing = (
        db.query(MoodCheckin)
        .filter(MoodCheckin.student_id == student_id)
        .order_by(MoodCheckin.created_at.desc())
        .first()
    )
    mood = latest_wellbeing.mood_score if latest_wellbeing else 5
    stress = latest_wellbeing.stress_level if latest_wellbeing else 5

    # Failed modules (assessments below 50%)
    failed_count = (
        db.query(Assessment)
        .filter(Assessment.student_id == student_id, Assessment.mark < 50)
        .count()
    )

    return {
        "academic_average": avg_mark,
        "assignment_completion": avg_mark * 0.9 + 10,  # approximate
        "failed_module_count": failed_count,
        "attendance_percentage": att_pct,
        "attendance_change": att_change,
        "study_hours_weekly": 12.0,  # default
        "lms_activity_score": avg_mark * 0.85 + 5,
        "mood_average": mood,
        "stress_average": stress,
    }


@router.post("/generate")
def generate_prediction(
    data: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student, UserRole.lecturer, UserRole.advisor, UserRole.admin)),
):
    student_id = data.student_id
    require_own_student_record(current_user, student_id, db)
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    used_ml = False

    # Try ML model first, fall back to formula
    if ml_available:
        try:
            features = _build_feature_vector(db, student_id)
            predictor = RiskPredictor()
            result = predictor.predict(features)
            risk_score = result["risk_score"]
            risk_level = RiskLevel(result["risk_level"])
            explanation = result["explanation"]
            factors = result["factors"]
            used_ml = True
        except Exception:
            used_ml = False

    if not used_ml:
        # Fallback: calculate risk score based on real data
        avg_mark = (
            db.query(func.avg(Assessment.mark))
            .filter(Assessment.student_id == student_id)
            .scalar()
            or 70
        )

        latest_att = (
            db.query(Attendance)
            .filter(Attendance.student_id == student_id)
            .order_by(Attendance.date.desc())
            .first()
        )
        att_pct = latest_att.attendance_percentage if latest_att else 85

        mark_factor = max(0, 100 - avg_mark) * 0.4
        att_factor = max(0, 100 - att_pct) * 0.6
        risk_score = min(100, mark_factor + att_factor)

        if risk_score <= 40:
            risk_level = RiskLevel.LOW
        elif risk_score <= 70:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.HIGH

        explanation = (
            f"Risk assessment based on academic average ({avg_mark:.0f}%) "
            f"and attendance ({att_pct:.0f}%). "
            f"{'Attendance below 70% is a significant factor.' if att_pct < 70 else ''}"
            f"{'Average mark below 50% contributes to risk.' if avg_mark < 50 else ''}"
        )

        factors = [
            {
                "factor": f"Academic average: {avg_mark:.0f}%",
                "impact": "High" if avg_mark < 60 else "Medium",
                "direction": "increase" if avg_mark < 60 else "decrease",
            },
            {
                "factor": f"Attendance: {att_pct:.0f}%",
                "impact": "High" if att_pct < 70 else "Medium",
                "direction": "increase" if att_pct < 70 else "decrease",
            },
        ]

    prediction = RiskPrediction(
        id=str(uuid.uuid4()),
        student_id=student_id,
        risk_score=round(risk_score, 1),
        risk_level=risk_level,
        explanation=explanation,
        model_version="ml_best_v1.0" if used_ml else "fallback_v1.0",
    )
    db.add(prediction)
    db.commit()

    # Generate recommendations
    generate_recommendations(db, student_id, risk_level.value)

    db.refresh(prediction)

    return {
        "risk_level": risk_level.value,
        "risk_score": round(risk_score, 1),
        "explanation": explanation,
        "factors": factors,
        "model_version": prediction.model_version,
        "created_at": prediction.created_at.isoformat() if prediction.created_at else "",
    }
