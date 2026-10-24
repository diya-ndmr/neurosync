from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from lms.models import AssessmentResult, AttendanceRecord, LMSActivity, QuizAttempt, Student


def extract_student_features(db: Session, student_id: str) -> dict[str, Any]:
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        raise ValueError("Student not found")

    attendance_records = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id).all()
    assessment_records = db.query(AssessmentResult).filter(AssessmentResult.student_id == student_id).all()
    quiz_attempts = db.query(QuizAttempt).filter(QuizAttempt.student_id == student_id).all()
    activity_records = db.query(LMSActivity).filter(LMSActivity.student_id == student_id).all()

    attendance_rate = 0.0
    if attendance_records:
        attendance_rate = sum(1 for r in attendance_records if r.status == "PRESENT") / len(attendance_records) * 100

    assessment_average = 0.0
    marked_assessments = [record.percentage for record in assessment_records if record.percentage is not None]
    if marked_assessments:
        assessment_average = sum(marked_assessments) / len(marked_assessments)

    quiz_average = 0.0
    marked_quizzes = [attempt.percentage for attempt in quiz_attempts if attempt.percentage is not None]
    if marked_quizzes:
        quiz_average = sum(marked_quizzes) / len(marked_quizzes)

    weekly_login_count = 0
    if activity_records:
        weekly_login_count = sum(1 for a in activity_records if a.activity_type == "LOGIN")

    days_since_last_login = 0
    if activity_records:
        latest = max(a.timestamp for a in activity_records)
        days_since_last_login = (datetime.utcnow() - latest.replace(tzinfo=None)).days

    return {
        "student_id": student_id,
        "attendance_rate_7d": round(attendance_rate, 2),
        "attendance_rate_30d": round(attendance_rate, 2),
        "attendance_change": 0.0,
        "assessment_average": round(assessment_average, 2),
        "assessment_change": 0.0,
        "quiz_average": round(quiz_average, 2),
        "quiz_change": 0.0,
        "missed_assessments": sum(1 for r in assessment_records if r.status == "MISSING"),
        "late_submissions": sum(1 for r in assessment_records if r.status == "LATE"),
        "days_since_last_login": days_since_last_login,
        "weekly_login_count": weekly_login_count,
        "resource_engagement": sum(1 for a in activity_records if a.activity_type in {"VIEW_RESOURCE", "DOWNLOAD_RESOURCE"}),
        "engagement_change": 0.0,
        "overall_average": round((assessment_average + quiz_average) / 2, 2),
        "performance_trend": "stable",
    }
