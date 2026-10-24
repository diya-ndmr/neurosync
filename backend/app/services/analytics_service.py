from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.student import StudentProfile
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.risk_prediction import RiskPrediction, RiskLevel
from app.models.module import Module
from lms.models import (
    Student as LMSStudent, 
    Assessment as LMSAssessment, 
    AssessmentResult as LMSAssessmentResult,
    Module as LMSModule, 
    Programme as LMSProgramme,
    MonthlyAttendanceSummary,
    Referral as LMSReferral,
)


def get_admin_analytics_lms(lms_db: Session) -> dict:
    """Build admin analytics only from recorded LMS data."""
    total_students = lms_db.query(LMSStudent).count()

    active_students = lms_db.query(LMSStudent).filter(func.upper(LMSStudent.enrolment_status) == "ACTIVE").count()
    avg_perf = lms_db.query(func.avg(LMSAssessmentResult.percentage)).scalar()
    average_performance = round(float(avg_perf), 1) if avg_perf is not None else None

    student_averages = (
        lms_db.query(LMSAssessmentResult.student_id, func.avg(LMSAssessmentResult.percentage))
        .filter(LMSAssessmentResult.percentage.isnot(None))
        .group_by(LMSAssessmentResult.student_id)
        .all()
    )
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for _, average in student_averages:
        level = "HIGH" if float(average) <= 50 else "MEDIUM" if float(average) < 75 else "LOW"
        risk_counts[level] += 1
    high_risk = risk_counts["HIGH"]

    att_trend_raw = (
        lms_db.query(
            MonthlyAttendanceSummary.month,
            func.avg(MonthlyAttendanceSummary.attendance_percentage).label("pct"),
        )
        .group_by(MonthlyAttendanceSummary.month)
        .order_by(MonthlyAttendanceSummary.month)
        .all()
    )
    
    attendance_trend = [{"month": r.month, "percentage": round(float(r.pct), 1)} for r in att_trend_raw]

    perf_trend_raw = (
        lms_db.query(
            func.substr(LMSAssessmentResult.submission_date, 1, 7).label("month_str"),
            func.avg(LMSAssessmentResult.percentage).label("avg"),
        )
        .filter(LMSAssessmentResult.submission_date.isnot(None))
        .filter(LMSAssessmentResult.percentage.isnot(None))
        .group_by(func.substr(LMSAssessmentResult.submission_date, 1, 7))
        .order_by("month_str")
        .all()
    )
    
    performance_trend = [{"month": r.month_str, "average": round(float(r.avg), 1)} for r in perf_trend_raw]

    programme_comparison = []
    prog_raw = (
        lms_db.query(
            LMSProgramme.programme_name,
            func.avg(LMSAssessmentResult.percentage).label("avg"),
            func.count(func.distinct(LMSStudent.student_id)).label("students"),
        )
        .select_from(LMSProgramme)
        .join(LMSStudent, LMSStudent.programme_id == LMSProgramme.programme_id)
        .join(LMSAssessmentResult, LMSAssessmentResult.student_id == LMSStudent.student_id)
        .filter(LMSAssessmentResult.percentage.isnot(None))
        .group_by(LMSProgramme.programme_name)
        .order_by(LMSProgramme.programme_name)
        .all()
    )
    programme_comparison = [
        {"programme": r.programme_name, "average": round(float(r.avg), 1), "students": r.students}
        for r in prog_raw
    ]

    # Retention requires a cohort and period baseline, neither of which is present.
    retention_rate = None
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    recent_referrals = lms_db.query(LMSReferral).filter(LMSReferral.created_at >= week_ago).all()
    new_referrals = len(recent_referrals)
    priority_referrals = sum(row.urgency == "PRIORITY" for row in recent_referrals)
    high_risk_referrals = sum(row.risk_level == "HIGH" for row in recent_referrals)
    
    return {
        "total_students": total_students,
        "active_students": active_students,
        "average_performance": average_performance,
        "retention_rate": retention_rate,
        "high_risk_students": high_risk,
        "risk_distribution": [
            {"name": "LOW", "value": risk_counts["LOW"]},
            {"name": "MEDIUM", "value": risk_counts["MEDIUM"]},
            {"name": "HIGH", "value": high_risk},
        ],
        "attendance_trend": attendance_trend,
        "performance_trend": performance_trend,
        "programme_comparison": programme_comparison,
        "weekly_intelligence": {
            "new_referrals": new_referrals,
            "priority_referrals": priority_referrals,
            "high_risk_referrals": high_risk_referrals,
        },
    }


def get_admin_analytics(db: Session) -> dict:
    total_students = db.query(StudentProfile).count()
    avg_perf_value = db.query(func.avg(Assessment.mark)).scalar()
    average_performance = round(float(avg_perf_value), 1) if avg_perf_value is not None else None

    latest_risk = (
        db.query(
            RiskPrediction.student_id.label("student_id"),
            RiskPrediction.risk_level.label("risk_level"),
            func.row_number().over(
                partition_by=RiskPrediction.student_id,
                order_by=(RiskPrediction.created_at.desc(), RiskPrediction.id.desc()),
            ).label("prediction_rank"),
        )
        .subquery()
    )
    risk_counts = dict(
        db.query(latest_risk.c.risk_level, func.count())
        .filter(latest_risk.c.prediction_rank == 1)
        .group_by(latest_risk.c.risk_level)
        .all()
    )
    low = risk_counts.get(RiskLevel.LOW, 0)
    medium = risk_counts.get(RiskLevel.MEDIUM, 0)
    high_risk = risk_counts.get(RiskLevel.HIGH, 0)

    # Build attendance trend from DB
    month_names = {
        1: "Mar", 2: "Apr", 3: "May", 4: "Jun", 5: "Jul", 6: "Aug",
        7: "Sep", 8: "Oct", 9: "Nov", 10: "Dec", 11: "Jan", 12: "Feb",
    }
    att_trend_raw = (
        db.query(
            extract("month", Attendance.date).label("month"),
            func.avg(Attendance.attendance_percentage).label("pct"),
        )
        .group_by(extract("month", Attendance.date))
        .order_by("month")
        .all()
    )
    attendance_trend = [
        {"month": month_names.get(int(r.month), f"M{r.month}"), "percentage": round(float(r.pct), 1)}
        for r in att_trend_raw
    ]

    # Build performance trend from DB
    perf_trend_raw = (
        db.query(
            extract("month", Assessment.assessment_date).label("month"),
            func.avg(Assessment.mark).label("avg"),
        )
        .group_by(extract("month", Assessment.assessment_date))
        .order_by("month")
        .all()
    )
    performance_trend = [
        {"month": month_names.get(int(r.month), f"M{r.month}"), "average": round(float(r.avg), 1)}
        for r in perf_trend_raw
    ]

    # Programme comparison from DB
    prog_raw = (
        db.query(
            Module.faculty,
            func.avg(Assessment.mark).label("avg"),
            func.count(func.distinct(StudentProfile.id)).label("students"),
        )
        .select_from(Module)
        .join(Assessment, Assessment.module_id == Module.id)
        .join(StudentProfile, StudentProfile.id == Assessment.student_id)
        .group_by(Module.faculty)
        .all()
    )
    programme_comparison = [
        {"programme": r.faculty, "average": round(float(r.avg), 1), "students": r.students}
        for r in prog_raw
    ]

    return {
        "total_students": total_students,
        "active_students": None,
        "average_performance": average_performance,
        "retention_rate": None,
        "high_risk_students": high_risk,
        "risk_distribution": [
            {"name": "LOW", "value": low},
            {"name": "MEDIUM", "value": medium},
            {"name": "HIGH", "value": high_risk},
        ],
        "attendance_trend": attendance_trend,
        "performance_trend": performance_trend,
        "programme_comparison": programme_comparison,
    }


def get_recovering_students(db: Session, limit: int = 50) -> list[dict]:
    """Return students whose three latest recorded risk levels show sustained recovery."""
    ranked_predictions = (
        db.query(
            RiskPrediction.id.label("prediction_id"),
            RiskPrediction.student_id.label("student_id"),
            RiskPrediction.risk_score.label("risk_score"),
            RiskPrediction.risk_level.label("risk_level"),
            RiskPrediction.model_version.label("model_version"),
            RiskPrediction.created_at.label("created_at"),
            func.row_number().over(
                partition_by=RiskPrediction.student_id,
                order_by=(RiskPrediction.created_at.desc(), RiskPrediction.id.desc()),
            ).label("prediction_rank"),
        )
        .subquery()
    )
    rows = (
        db.query(
            ranked_predictions.c.prediction_id,
            ranked_predictions.c.student_id,
            ranked_predictions.c.risk_score,
            ranked_predictions.c.risk_level,
            ranked_predictions.c.model_version,
            ranked_predictions.c.created_at,
            StudentProfile,
        )
        .join(StudentProfile, StudentProfile.id == ranked_predictions.c.student_id)
        .filter(ranked_predictions.c.prediction_rank <= 3)
        .order_by(ranked_predictions.c.student_id, ranked_predictions.c.prediction_rank.desc())
        .all()
    )
    predictions_by_student: dict[str, list[dict[str, Any]]] = {}
    profiles_by_student: dict[str, StudentProfile] = {}
    for prediction_id, student_id, risk_score, risk_level, model_version, created_at, profile in rows:
        predictions_by_student.setdefault(student_id, []).append({
            "id": prediction_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "model_version": model_version,
            "created_at": created_at,
        })
        profiles_by_student[student_id] = profile

    recovering = []
    for student_id, predictions in predictions_by_student.items():
        latest = predictions[-3:]
        if len(latest) < 3 or [item["risk_level"] for item in latest] != [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            continue
        profile = profiles_by_student[student_id]
        recovering.append({
            "student_id": student_id,
            "student_name": f"{profile.first_name} {profile.surname}",
            "programme": profile.programme,
            "year_level": profile.year_level,
            "risk_history": [
                {
                    "risk_level": item["risk_level"].value,
                    "risk_score": item["risk_score"],
                    "model_version": item["model_version"],
                    "created_at": item["created_at"].isoformat() if item["created_at"] else None,
                }
                for item in latest
            ],
            "latest_updated_at": latest[-1]["created_at"].isoformat() if latest[-1]["created_at"] else None,
        })

    recovering.sort(key=lambda item: item["latest_updated_at"] or "", reverse=True)
    return recovering[:limit]


def get_radar_insights(db: Session, limit: int = 100) -> list[dict]:
    """Build admin Radar insights from the latest two recorded risk snapshots."""
    ranked_predictions = (
        db.query(
            RiskPrediction.id.label("prediction_id"),
            RiskPrediction.student_id.label("student_id"),
            RiskPrediction.risk_score.label("risk_score"),
            RiskPrediction.risk_level.label("risk_level"),
            RiskPrediction.created_at.label("created_at"),
            func.row_number().over(
                partition_by=RiskPrediction.student_id,
                order_by=(RiskPrediction.created_at.desc(), RiskPrediction.id.desc()),
            ).label("prediction_rank"),
        )
        .subquery()
    )
    rows = (
        db.query(
            ranked_predictions.c.prediction_id,
            ranked_predictions.c.student_id,
            ranked_predictions.c.risk_score,
            ranked_predictions.c.risk_level,
            ranked_predictions.c.created_at,
            ranked_predictions.c.prediction_rank,
            StudentProfile,
        )
        .join(StudentProfile, StudentProfile.id == ranked_predictions.c.student_id)
        .filter(ranked_predictions.c.prediction_rank <= 3)
        .order_by(ranked_predictions.c.student_id, ranked_predictions.c.prediction_rank.desc())
        .all()
    )

    history_by_student: dict[str, list[dict[str, Any]]] = {}
    profile_by_student: dict[str, StudentProfile] = {}
    for prediction_id, student_id, score, level, created_at, rank, profile in rows:
        history_by_student.setdefault(student_id, []).append({
            "id": prediction_id,
            "score": float(score),
            "level": level,
            "created_at": created_at,
            "rank": rank,
        })
        profile_by_student[student_id] = profile

    insights = []
    ordered_levels = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
    for student_id, history in history_by_student.items():
        profile = profile_by_student[student_id]
        latest = history[-1]
        previous = history[-2] if len(history) > 1 else None
        common = {
            "student_id": student_id,
            "student_name": f"{profile.first_name} {profile.surname}",
            "programme": profile.programme,
            "observed_at": latest["created_at"].isoformat() if latest["created_at"] else None,
        }
        if len(history) >= 3 and [item["level"] for item in history[-3:]] == [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            recovery_history = history[-3:]
            insights.append({
                **common,
                "category": "IMPROVING",
                "title": "Recorded risk levels show sustained improvement",
                "evidence": [
                    "Three consecutive recorded levels progressed HIGH → MEDIUM → LOW.",
                    "Latest recorded score is " + f"{latest['score']:.1f}%." ,
                ],
                "record_ids": [item["id"] for item in recovery_history],
            })
        elif previous and (
            latest["score"] - previous["score"] >= 15
            or ordered_levels[latest["level"]] > ordered_levels[previous["level"]]
        ):
            insights.append({
                **common,
                "category": "EMERGING_RISK",
                "title": "Risk indicators increased",
                "evidence": [
                    f"Recorded risk changed from {previous['level'].value} ({previous['score']:.1f}%) "
                    f"to {latest['level'].value} ({latest['score']:.1f}%).",
                    f"Previous assessment: {previous['created_at'].isoformat() if previous['created_at'] else 'date unavailable'}; "
                    f"latest assessment: {latest['created_at'].isoformat() if latest['created_at'] else 'date unavailable'}.",
                ],
                "record_ids": [previous["id"], latest["id"]],
            })
        elif latest["level"] in {RiskLevel.HIGH, RiskLevel.MEDIUM}:
            insights.append({
                **common,
                "category": "WATCH",
                "title": f"Latest recorded risk is {latest['level'].value.lower()}",
                "evidence": [f"Latest recorded risk score is {latest['score']:.1f}% ({latest['level'].value})."],
                "record_ids": [latest["id"]],
            })

    missing_predictions = (
        db.query(StudentProfile)
        .outerjoin(RiskPrediction, RiskPrediction.student_id == StudentProfile.id)
        .filter(RiskPrediction.id.is_(None))
        .order_by(StudentProfile.id)
        .limit(limit)
        .all()
    )
    insights.extend({
        "category": "DATA_ISSUE",
        "title": "No risk prediction is recorded",
        "student_id": profile.id,
        "student_name": f"{profile.first_name} {profile.surname}",
        "programme": profile.programme,
        "observed_at": None,
        "evidence": ["This student profile has no recorded risk prediction."],
        "record_ids": [],
    } for profile in missing_predictions)

    priority = {"EMERGING_RISK": 0, "WATCH": 1, "DATA_ISSUE": 2, "IMPROVING": 3}
    insights.sort(key=lambda item: item["observed_at"] or "", reverse=True)
    insights.sort(key=lambda item: priority[item["category"]])
    return insights[:max(1, min(limit, 100))]


def answer_admin_intelligence_question(db: Session, question: str) -> dict:
    """Resolve supported admin questions through fixed, permission-checked data services."""
    normalized = " ".join(question.casefold().split())
    if any(term in normalized for term in ("recover", "improv", "getting better")):
        items = [
            {
                **item,
                "category": "IMPROVING",
                "title": "Recorded risk levels show sustained improvement",
                "evidence": [
                    "Three latest recorded levels progressed HIGH → MEDIUM → LOW.",
                    "Recorded scores: " + " → ".join(f"{snapshot['risk_score']:.1f}%" for snapshot in item["risk_history"]) + ".",
                ],
            }
            for item in get_recovering_students(db, limit=100)
        ]
        return {
            "supported": True,
            "answer": f"{len(items)} student(s) have a recorded High → Medium → Low risk sequence.",
            "items": items,
        }

    if any(term in normalized for term in ("missing prediction", "data issue", "no prediction")):
        items = [item for item in get_radar_insights(db, limit=100) if item["category"] == "DATA_ISSUE"]
        return {
            "supported": True,
            "answer": f"{len(items)} student(s) have no recorded risk prediction.",
            "items": items,
        }

    if any(term in normalized for term in ("attention", "at risk", "high risk", "emerging risk", "watch")):
        items = [
            item for item in get_radar_insights(db, limit=100)
            if item["category"] in {"EMERGING_RISK", "WATCH"}
        ]
        return {
            "supported": True,
            "answer": f"{len(items)} student(s) have recorded Emerging Risk or Watch signals.",
            "items": items,
        }

    return {
        "supported": False,
        "answer": "I can answer questions about students requiring attention, recorded recovery sequences, or missing risk predictions.",
        "items": [],
    }
