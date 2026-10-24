from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from lms.models import (
    AcademicSnapshot,
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    MonthlyAttendanceSummary,
    Intervention,
    LMSActivity,
    Lecturer,
    ModuleEnrolment,
    Quiz,
    QuizAttempt,
    Referral,
    Student,
    StudentMapping,
    DatasetImport,
    StaffMapping,
    Submission,
    WorkflowEvent,
)

STRATEGIES = (
    "Academic Advisor Check-In",
    "Lecturer Consultation",
    "Academic Planning Session",
    "Time Management Support",
    "Study Skills Support",
    "Attendance Support",
    "Assessment Recovery Plan",
    "Peer Tutoring Referral",
    "Tutoring / Academic Support Referral",
    "Learning Resource Guidance",
    "Student Support Services Referral",
    "Follow-Up Monitoring",
    "Engagement Check-In",
)


def _percentage(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


# ── Explainable risk scoring ────────────────────────────────────────────────
# Each criterion contributes a documented share of the 0-100 scale. The caps are
# deliberately *above* the MEDIUM threshold (40) so that a single severe signal can
# raise a flag: previously attendance decline was capped at 30 and missing work at
# 35, which meant a student whose attendance collapsed by 30 percentage points - or
# who had seven assessments missing - was still reported as LOW risk and never
# appeared in an advisor queue.
RISK_LEVEL_MEDIUM = 40.0
RISK_LEVEL_HIGH = 70.0
ATTENDANCE_DECLINE_POINTS = 45.0
ATTENDANCE_DECLINE_FULL_SCALE = 30.0  # percentage points that earn the full 45
MISSING_SUBMISSION_POINTS = 40.0
MISSING_SUBMISSION_FULL_SCALE = 6  # missing assessments that earn the full 40
DECLINING_MARKS_POINTS = 25.0
ENGAGEMENT_DROP_POINTS = 15.0


def risk_level_for(score: float) -> str:
    if score >= RISK_LEVEL_HIGH:
        return "HIGH"
    if score >= RISK_LEVEL_MEDIUM:
        return "MEDIUM"
    return "LOW"


def academic_risk_level(mark: float) -> str:
    """Classify academic performance using the university's mark bands."""
    if mark <= 50:
        return "HIGH"
    if mark < 75:
        return "MEDIUM"
    return "LOW"


def score_risk_signal(
    *,
    attendance_change: float,
    missing_submissions: int,
    assessment_trend: str,
    engagement_dropped: bool,
) -> dict[str, Any]:
    """Score the recorded LMS indicators and explain every contribution.

    The result is evidence-based monitoring, not a prediction: it states which
    recorded indicator moved and by how much.
    """
    evidence: list[str] = []
    score = 0.0

    if attendance_change <= -10:
        evidence.append(
            f"Attendance declined by {abs(attendance_change):.0f} percentage points over the last 30 days."
        )
        score += ATTENDANCE_DECLINE_POINTS * min(1.0, abs(attendance_change) / ATTENDANCE_DECLINE_FULL_SCALE)
    if missing_submissions:
        evidence.append(f"{missing_submissions} assessment submission(s) are recorded as missing.")
        score += MISSING_SUBMISSION_POINTS * min(1.0, missing_submissions / MISSING_SUBMISSION_FULL_SCALE)
    if assessment_trend == "declining":
        evidence.append("Recent assessment marks are lower than the previous assessment period.")
        score += DECLINING_MARKS_POINTS
    if engagement_dropped:
        evidence.append("LMS activity decreased compared with the preceding 30-day period.")
        score += ENGAGEMENT_DROP_POINTS

    score = round(min(score, 100.0), 1)
    if not evidence:
        evidence.append("No significant negative trend was detected in the available LMS indicators.")
    return {"risk_score": score, "risk_level": risk_level_for(score), "evidence": evidence}


def classify_risk_trajectory(
    *,
    attendance_change: float,
    assessment_trend: str,
    engagement_dropped: bool,
    engagement_increased: bool,
) -> dict[str, Any]:
    """Summarize observed indicator direction without forecasting outcomes."""
    worsening = []
    improving = []
    if attendance_change <= -8:
        worsening.append(f"Attendance declined by {abs(attendance_change):.0f} percentage points over the last 30 days.")
    elif attendance_change >= 8:
        improving.append(f"Attendance improved by {attendance_change:.0f} percentage points over the last 30 days.")
    if assessment_trend == "declining":
        worsening.append("Recent assessment marks are lower than the previous assessment period.")
    elif assessment_trend == "improving":
        improving.append("Recent assessment marks are higher than the previous assessment period.")
    if engagement_dropped:
        worsening.append("LMS activity decreased compared with the preceding 30-day period.")
    elif engagement_increased:
        improving.append("LMS activity increased compared with the preceding 30-day period.")

    if worsening and improving:
        trajectory = "stable"
    elif len(worsening) >= 2:
        trajectory = "rapidly_deteriorating"
    elif worsening:
        trajectory = "slowly_deteriorating"
    elif len(improving) >= 2:
        trajectory = "improving"
    else:
        trajectory = "stable"

    return {"trajectory": trajectory, "evidence": worsening + improving}


def ensure_fictional_student_emails(db: Session) -> None:
    dataset_imported = db.query(DatasetImport).count() > 0
    if not dataset_imported:
        students = db.query(Student).all()
        changed = False
        for student in students:
            expected = f"{student.student_id.lower()}@student.neurosync.demo"
            if student.institutional_email != expected:
                student.institutional_email = expected
                changed = True
        if changed:
            db.commit()
    if not dataset_imported and db.query(StudentMapping).filter(StudentMapping.app_user_email == "sarah@university.edu").first() is None:
        first_student = db.query(Student).order_by(Student.student_id).first()
        if first_student is not None:
            db.add(StudentMapping(app_user_email="sarah@university.edu", student_id=first_student.student_id))
            db.commit()
    if not dataset_imported and db.query(StaffMapping).filter(StaffMapping.app_user_email == "lecturer@university.edu").first() is None:
        first_lecturer = db.query(Lecturer).order_by(Lecturer.lecturer_id).first()
        if first_lecturer is not None:
            db.add(StaffMapping(app_user_email="lecturer@university.edu", lecturer_id=first_lecturer.lecturer_id))
            db.commit()


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def build_student_review(db: Session, student_id: str) -> dict[str, Any]:
    student = (
        db.query(Student)
        .options(joinedload(Student.programme))
        .filter(Student.student_id == student_id)
        .first()
    )
    if student is None:
        raise ValueError("Student not found")

    today = date.today()
    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=30)
    since_7d = now - timedelta(days=7)
    enrolments = (
        db.query(ModuleEnrolment)
        .options(joinedload(ModuleEnrolment.module))
        .filter(ModuleEnrolment.student_id == student_id)
        .all()
    )
    module_ids = {row.module_id for row in enrolments}
    attendance = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceRecord.session_date.desc())
        .all()
    )
    monthly_attendance = (
        db.query(MonthlyAttendanceSummary)
        .filter(MonthlyAttendanceSummary.student_id == student_id)
        .order_by(MonthlyAttendanceSummary.month.desc())
        .all()
    )
    assessments = (
        db.query(AssessmentResult)
        .options(joinedload(AssessmentResult.assessment).joinedload(Assessment.module))
        .filter(AssessmentResult.student_id == student_id)
        .all()
    )
    quizzes = (
        db.query(QuizAttempt)
        .options(joinedload(QuizAttempt.quiz).joinedload(Quiz.module))
        .filter(QuizAttempt.student_id == student_id)
        .all()
    )
    submissions = (
        db.query(Submission)
        .options(joinedload(Submission.assessment).joinedload(Assessment.module))
        .filter(Submission.student_id == student_id)
        .all()
    )
    activity = (
        db.query(LMSActivity)
        .filter(LMSActivity.student_id == student_id)
        .order_by(LMSActivity.timestamp.desc())
        .all()
    )

    present_statuses = {"PRESENT", "LATE"}
    attendance_30 = [record for record in attendance if record.session_date >= today - timedelta(days=30)]
    attendance_7 = [record for record in attendance if record.session_date >= today - timedelta(days=7)]
    attendance_rate = _percentage(sum(record.status in present_statuses for record in attendance), len(attendance))
    attendance_30_rate = _percentage(sum(record.status in present_statuses for record in attendance_30), len(attendance_30))
    attendance_7_rate = _percentage(sum(record.status in present_statuses for record in attendance_7), len(attendance_7))
    attendance_is_aggregated = False
    if not attendance and monthly_attendance:
        eligible_sessions = sum(row.scheduled_sessions - row.approved_leave_sessions for row in monthly_attendance)
        attended = sum(row.attended_sessions for row in monthly_attendance)
        attendance_rate = _percentage(attended, eligible_sessions)
        attendance_30_rate = monthly_attendance[0].attendance_percentage
        attendance_7_rate = 0.0
        attendance_is_aggregated = True

    current_results = [row for row in assessments if row.assessment is not None and row.assessment.due_date <= today]
    submitted = [row for row in submissions if row.status in {"SUBMITTED", "LATE"}]
    missing = [row for row in submissions if row.status == "MISSING"]
    late = [row for row in submissions if row.status == "LATE"]
    quiz_average = _average([row.percentage for row in quizzes])
    academic_average = _average([
        row.percentage
        for row in current_results
        if row.status != "MISSING" and row.percentage is not None
    ])
    engagement_items = [row for row in activity if row.timestamp.replace(tzinfo=timezone.utc) >= since_30d]
    last_login = next((row.timestamp for row in activity if row.activity_type == "LOGIN"), None)
    this_week_logins = sum(
        row.activity_type == "LOGIN" and row.timestamp.replace(tzinfo=timezone.utc) >= since_7d
        for row in activity
    )
    activity_counts = Counter(row.activity_type for row in engagement_items)
    engagement_score = round(
        min(100.0, len(engagement_items) * 0.5 + sum(row.activity_type == "DISCUSSION_POST" for row in engagement_items) * 2), 1
    )
    engagement_previous = [
        row for row in activity
        if since_30d - timedelta(days=30) <= row.timestamp.replace(tzinfo=timezone.utc) < since_30d
    ]

    assessment_trend = _trend(
        [
            row.percentage
            for row in current_results
            if row.percentage is not None
            and row.assessment is not None
            and row.assessment.due_date > today - timedelta(days=42)
        ],
        [
            row.percentage
            for row in current_results
            if row.percentage is not None
            and row.assessment is not None
            and today - timedelta(days=84) < row.assessment.due_date <= today - timedelta(days=42)
        ],
    )
    previous_attendance = [record for record in attendance if today - timedelta(days=60) <= record.session_date < today - timedelta(days=30)]
    if attendance_is_aggregated and len(monthly_attendance) >= 2:
        attendance_change = round(monthly_attendance[0].attendance_percentage - monthly_attendance[1].attendance_percentage, 1)
    else:
        attendance_change = round(attendance_30_rate - _percentage(sum(r.status in present_statuses for r in previous_attendance), len(previous_attendance)), 1)

    engagement_dropped = bool(engagement_previous) and len(engagement_items) < len(engagement_previous) * 0.7
    engagement_increased = bool(engagement_previous) and len(engagement_items) >= len(engagement_previous) * 1.3
    trajectory = classify_risk_trajectory(
        attendance_change=attendance_change,
        assessment_trend=assessment_trend,
        engagement_dropped=engagement_dropped,
        engagement_increased=engagement_increased,
    )
    risk = score_risk_signal(
        attendance_change=attendance_change,
        missing_submissions=len(missing),
        assessment_trend=assessment_trend,
        engagement_dropped=engagement_dropped,
    )
    score = round(academic_average, 1)
    level = academic_risk_level(academic_average)
    evidence = risk["evidence"]

    due_assessments = db.query(Assessment).filter(Assessment.module_id.in_(module_ids), Assessment.due_date <= today).all() if module_ids else []
    quiz_total = db.query(Quiz).filter(Quiz.module_id.in_(module_ids), Quiz.available_date <= today).count() if module_ids else 0
    referral_rows = db.query(Referral).filter(Referral.student_id == student_id).order_by(Referral.created_at.desc()).all()
    intervention_rows = db.query(Intervention).filter(Intervention.student_id == student_id).order_by(Intervention.created_at.desc()).all()
    shared_events = db.query(WorkflowEvent).filter(
        WorkflowEvent.student_id == student_id,
        WorkflowEvent.visibility == "SHARED",
    ).order_by(WorkflowEvent.occurred_at.asc()).all()

    return {
        "student": {
            "student_id": student.student_id,
            "name": f"{student.first_name} {student.surname}",
            "programme": student.programme.programme_name if student.programme is not None else student.programme_id,
            "faculty": student.programme.faculty if student.programme is not None else "Not recorded",
            "year_of_study": student.year_of_study,
            "institutional_email": student.institutional_email,
            "enrolment_status": student.enrolment_status,
        },
        "modules": [
            {"module_id": row.module_id, "module_code": row.module.module_code, "module_name": row.module.module_name}
            for row in enrolments if row.module is not None
        ],
        "metrics": {
            "academic_average": academic_average,
            "attendance": attendance_rate,
            "attendance_30d": attendance_30_rate,
            "attendance_7d": attendance_7_rate,
            "attendance_change_30d": attendance_change,
            "classes_attended": sum(row.status in present_statuses for row in attendance),
            "classes_missed": sum(row.status == "ABSENT" for row in attendance),
            "late_arrivals": sum(row.status == "LATE" for row in attendance),
            "submission_rate": _percentage(len(submitted), len(due_assessments)),
            "late_submissions": len(late),
            "missing_submissions": len(missing),
            "quiz_average": quiz_average,
            "quiz_completion_rate": _percentage(len(quizzes), quiz_total),
            "last_login": last_login.isoformat() if last_login else None,
            "days_since_last_login": (now - last_login.replace(tzinfo=timezone.utc)).days if last_login else None,
            "logins_this_week": this_week_logins,
            "resources_viewed": activity_counts["VIEW_RESOURCE"],
            "resources_downloaded": activity_counts["DOWNLOAD_RESOURCE"],
            "assessment_pages_viewed": activity_counts["VIEW_ASSESSMENT"],
            "quiz_activity": activity_counts["QUIZ_ATTEMPT"],
            "discussion_activity": activity_counts["DISCUSSION_VIEW"] + activity_counts["DISCUSSION_POST"],
            "engagement_score": engagement_score,
            "assessment_trend": assessment_trend,
        },
        "attendance": [
            {"date": row.session_date.isoformat(), "session": row.session.session_type if row.session else "CLASS", "module_id": row.module_id, "status": row.status}
            for row in attendance
        ] if attendance else [
            {
                "date": f"{row.month}-01",
                "session": "MONTHLY SUMMARY",
                "module_id": "AGGREGATE",
                "status": f"{row.attendance_percentage:.1f}% attendance; {row.approved_leave_sessions} approved leave sessions",
            }
            for row in monthly_attendance
        ],
        "submissions": [
            {
                "submission_id": row.submission_id,
                "assessment_id": row.assessment_id,
                "assessment": row.assessment.title,
                "module_id": row.assessment.module_id,
                "module_code": row.assessment.module.module_code if row.assessment.module else "",
                "type": row.assessment.assessment_type,
                "due_date": row.assessment.due_date.isoformat(),
                "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
                "status": row.status,
                "mark": next((result.percentage for result in assessments if result.assessment_id == row.assessment_id), None),
                "weight": row.assessment.weight,
                "feedback": None,
            }
            for row in submissions if row.assessment is not None
        ],
        "assessments": [
            {
                "assessment_id": row.assessment_id,
                "assessment": row.assessment.title,
                "type": row.assessment.assessment_type,
                "module_id": row.assessment.module_id,
                "module_code": row.assessment.module.module_code if row.assessment.module else "",
                "due_date": row.assessment.due_date.isoformat(),
                "weight": row.assessment.weight,
                "mark": row.percentage,
                "status": row.status,
            }
            for row in assessments if row.assessment is not None
        ],
        "quizzes": [
            {
                "quiz": row.quiz.title,
                "module_code": row.quiz.module.module_code if row.quiz is not None and row.quiz.module is not None else "",
                "attempt": row.attempt_number,
                "score": row.score,
                "percentage": row.percentage,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration": row.duration,
            }
            for row in quizzes if row.quiz is not None
        ],
        "risk": {
            "risk_level": level,
            "risk_score": score,
            "evidence": evidence,
            "trajectory": trajectory["trajectory"],
            "trajectory_evidence": trajectory["evidence"],
        },
        "referrals": [_referral_json(row) for row in referral_rows],
        "interventions": [_intervention_json(row) for row in intervention_rows],
        "timeline": [
            {"event_type": event.event_type, "summary": event.summary, "occurred_at": event.occurred_at.isoformat()}
            for event in shared_events
        ],
    }


def build_assessment_intelligence(db: Session, module_id: str) -> dict[str, Any]:
    """Compare recent completed assessment cohort averages without inferring cause."""
    assessments = (
        db.query(
            Assessment.assessment_id,
            Assessment.title,
            Assessment.due_date,
            func.avg(AssessmentResult.percentage).label("average"),
            func.count(AssessmentResult.result_id).label("student_count"),
        )
        .join(AssessmentResult, AssessmentResult.assessment_id == Assessment.assessment_id)
        .filter(
            Assessment.module_id == module_id,
            Assessment.due_date <= date.today(),
            AssessmentResult.status.in_(["SUBMITTED", "LATE"]),
        )
        .group_by(Assessment.assessment_id, Assessment.title, Assessment.due_date)
        .order_by(Assessment.due_date.desc(), Assessment.assessment_id.desc())
        .limit(2)
        .all()
    )

    if len(assessments) < 2:
        return {
            "module_id": module_id,
            "status": "INSUFFICIENT_DATA",
            "message": "At least two completed assessments are needed for comparison.",
            "comparison": None,
        }

    current, previous = assessments
    current_average = round(float(current.average), 1)
    previous_average = round(float(previous.average), 1)
    comparison = {
        "current_assessment": current.title,
        "current_due_date": current.due_date.isoformat(),
        "current_average": current_average,
        "current_student_count": current.student_count,
        "previous_assessment": previous.title,
        "previous_due_date": previous.due_date.isoformat(),
        "previous_average": previous_average,
        "previous_student_count": previous.student_count,
        "change_percentage_points": round(current_average - previous_average, 1),
    }

    if min(current.student_count, previous.student_count) < 3:
        return {
            "module_id": module_id,
            "status": "INSUFFICIENT_COHORT",
            "message": "At least three submitted results per assessment are needed for a cohort signal.",
            "comparison": comparison,
        }

    change = comparison["change_percentage_points"]
    anomaly = change <= -10
    return {
        "module_id": module_id,
        "status": "ANOMALY_DETECTED" if anomaly else "NO_ANOMALY_DETECTED",
        "message": (
            f"The cohort average declined by {abs(change):.1f} percentage points between "
            f"{previous.title} and {current.title}."
            if anomaly
            else f"The cohort average changed by {change:+.1f} percentage points between "
            f"{previous.title} and {current.title}; no 10-point decline signal was detected."
        ),
        "comparison": comparison,
        "interpretation": "Observed cohort change only; this comparison does not establish a cause.",
    }


def _trend(recent: list[float], previous: list[float]) -> str:
    if not recent or not previous:
        return "stable"
    delta = _average(recent) - _average(previous)
    return "improving" if delta >= 5 else "declining" if delta <= -5 else "stable"


def recommend_strategies(review: dict[str, Any]) -> list[dict[str, str]]:
    metrics = review["metrics"]
    suggestions: list[dict[str, str]] = []
    if metrics["attendance_change_30d"] <= -10 or metrics["attendance"] < 70:
        suggestions.append({"strategy": "Attendance Support", "reason": "Recent attendance records show low or declining attendance."})
    if metrics["missing_submissions"] or metrics["late_submissions"] >= 2:
        suggestions.append({"strategy": "Academic Planning Session", "reason": "Submission records show missing or repeated late work."})
    if metrics["assessment_trend"] == "declining" or metrics["academic_average"] < 50:
        suggestions.append({"strategy": "Lecturer Consultation", "reason": "Assessment results show low or declining marks."})
    if metrics["engagement_score"] < 25:
        suggestions.append({"strategy": "Engagement Check-In", "reason": "Recorded LMS learning activity is limited in the last 30 days."})
    if len(suggestions) > 1:
        suggestions.append({"strategy": "Academic Advisor Check-In", "reason": "Multiple academic indicators may benefit from a broader support conversation."})
    return suggestions


def draft_supportive_email(review: dict[str, Any]) -> dict[str, str]:
    metrics = review["metrics"]
    topics = []
    if metrics["attendance"] < 80 or metrics["attendance_change_30d"] <= -8:
        topics.append("attendance")
    if metrics["missing_submissions"] or metrics["late_submissions"]:
        topics.append("assessment submissions")
    if metrics["assessment_trend"] == "declining" or metrics["academic_average"] < 55:
        topics.append("recent assessment results")
    if metrics["engagement_score"] < 25:
        topics.append("learning activity")
    opening = (
        f"We have noticed some recent changes in your {', '.join(topics)} and would like to check in."
        if topics else "We would like to check in and hear how your studies are going."
    )
    return {
        "subject": "A NeuroSync academic support check-in",
        "body": (
            f"Hello {review['student']['name']},\n\n{opening} "
            "We would be glad to arrange a short meeting to discuss how things are going and whether any academic support may be helpful. "
            "Academic indicators do not explain personal circumstances, and we will not make assumptions. "
            "Please let us know a time that works for you.\n\nKind regards,\nAcademic Advising"
        ),
    }


SNAPSHOT_LABEL_BEFORE = "BEFORE_INTERVENTION"

# (metric key, human label, unit, higher values are better)
_COMPARISON_INDICATORS: tuple[tuple[str, str, str, bool], ...] = (
    ("attendance", "Attendance", "%", True),
    ("attendance_30d", "Attendance (last 30 days)", "%", True),
    ("academic_average", "Average assessment mark", "%", True),
    ("submission_rate", "Submission rate", "%", True),
    ("engagement_score", "LMS engagement", "", True),
    ("quiz_average", "Quiz average", "%", True),
    ("missing_submissions", "Missing submissions", "", False),
    ("late_submissions", "Late submissions", "", False),
)

_COMPARISON_CAVEAT = "Correlation is not causation."

_COMPARISON_SUMMARY = {
    "IMPROVED": "Academic indicators improved following the recorded intervention.",
    "DECLINED": "Academic indicators declined following the recorded intervention.",
    "MIXED": "Academic indicators moved in different directions following the recorded intervention.",
    "UNCHANGED": "Academic indicators are broadly unchanged following the recorded intervention.",
}


def capture_academic_snapshot(db: Session, referral: Referral, review: dict[str, Any],
                              captured_by: str | None = None,
                              label: str = SNAPSHOT_LABEL_BEFORE) -> AcademicSnapshot:
    """Store the academic indicators once per referral and label.

    Repeated calls return the original snapshot so the comparison baseline stays
    fixed even if the student record changes later.
    """
    existing = (
        db.query(AcademicSnapshot)
        .filter(AcademicSnapshot.referral_id == referral.referral_id, AcademicSnapshot.label == label)
        .first()
    )
    if existing is not None:
        return existing
    metrics = review["metrics"]
    snapshot = AcademicSnapshot(
        referral_id=referral.referral_id,
        student_id=referral.student_id,
        captured_by=captured_by,
        label=label,
        attendance=float(metrics["attendance"]),
        attendance_30d=float(metrics["attendance_30d"]),
        academic_average=float(metrics["academic_average"]),
        submission_rate=float(metrics["submission_rate"]),
        engagement_score=float(metrics["engagement_score"]),
        missing_submissions=int(metrics["missing_submissions"]),
        late_submissions=int(metrics["late_submissions"]),
        quiz_average=float(metrics["quiz_average"]),
        risk_level=review["risk"]["risk_level"],
        risk_score=float(review["risk"]["risk_score"]),
    )
    db.add(snapshot)
    return snapshot


def _snapshot_metrics(snapshot: AcademicSnapshot) -> dict[str, float]:
    return {
        "attendance": round(snapshot.attendance, 1),
        "attendance_30d": round(snapshot.attendance_30d, 1),
        "academic_average": round(snapshot.academic_average, 1),
        "submission_rate": round(snapshot.submission_rate, 1),
        "engagement_score": round(snapshot.engagement_score, 1),
        "quiz_average": round(snapshot.quiz_average, 1),
        "missing_submissions": float(snapshot.missing_submissions),
        "late_submissions": float(snapshot.late_submissions),
    }


def build_intervention_comparison(db: Session, referral: Referral,
                                  review: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Compare the recorded pre-intervention snapshot with the current indicators.

    The system never judges whether an intervention "worked": this function only
    reports recorded numeric movement and always labels it as correlation.
    """
    snapshot = (
        db.query(AcademicSnapshot)
        .filter(AcademicSnapshot.referral_id == referral.referral_id, AcademicSnapshot.label == SNAPSHOT_LABEL_BEFORE)
        .first()
    )
    if snapshot is None:
        return None
    current_review = review if review is not None else build_student_review(db, referral.student_id)
    current_metrics = current_review["metrics"]
    baseline_metrics = _snapshot_metrics(snapshot)

    changes: list[dict[str, Any]] = []
    improved = 0
    declined = 0
    for key, label_text, unit, higher_is_better in _COMPARISON_INDICATORS:
        before = float(baseline_metrics[key])
        after = float(current_metrics[key])
        delta = round(after - before, 1)
        tolerance = 1.0 if unit == "%" else 0.0
        if abs(delta) <= tolerance:
            direction = "UNCHANGED"
        elif (delta > 0) == higher_is_better:
            direction = "IMPROVED"
            improved += 1
        else:
            direction = "DECLINED"
            declined += 1
        changes.append({
            "metric": key,
            "label": label_text,
            "unit": unit,
            "before": before,
            "current": after,
            "change": delta,
            "direction": direction,
        })

    if improved and declined:
        direction = "MIXED"
    elif improved:
        direction = "IMPROVED"
    elif declined:
        direction = "DECLINED"
    else:
        direction = "UNCHANGED"

    intervention_count = db.query(Intervention).filter(Intervention.referral_id == referral.referral_id).count()
    if intervention_count == 0:
        summary = (
            "A baseline was recorded when the student was referred and no intervention has been recorded yet, "
            "so this comparison only shows change since the referral date."
        )
    else:
        summary = _COMPARISON_SUMMARY[direction]

    return {
        "referral_id": referral.referral_id,
        "student_id": referral.student_id,
        "baseline_captured_at": snapshot.captured_at.isoformat(),
        "baseline_risk_level": snapshot.risk_level,
        "baseline_risk_score": round(snapshot.risk_score, 1),
        "current_risk_level": current_review["risk"]["risk_level"],
        "current_risk_score": current_review["risk"]["risk_score"],
        "has_recorded_intervention": intervention_count > 0,
        "intervention_count": intervention_count,
        "direction": direction,
        "summary": summary,
        "caveat": _COMPARISON_CAVEAT,
        "changes": changes,
    }


def record_event(db: Session, student_id: str, actor_id: str | None, event_type: str, summary: str,
                 referral_id: str | None = None, visibility: str = "SHARED") -> WorkflowEvent:
    event = WorkflowEvent(
        student_id=student_id,
        actor_id=actor_id,
        referral_id=referral_id,
        event_type=event_type,
        summary=summary,
        visibility=visibility,
    )
    db.add(event)
    return event


def _referral_json(row: Referral) -> dict[str, Any]:
    return {
        "referral_id": row.referral_id,
        "student_id": row.student_id,
        "lecturer_id": row.lecturer_id,
        "advisor_user_id": row.advisor_user_id,
        "module_id": row.module_id,
        "risk_level": row.risk_level,
        "risk_score": row.risk_score,
        "reason": row.reason,
        "lecturer_notes": row.lecturer_notes,
        "urgency": row.urgency,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


def _intervention_json(row: Intervention) -> dict[str, Any]:
    return {
        "intervention_id": row.intervention_id,
        "referral_id": row.referral_id,
        "strategy": row.strategy,
        "reason": row.reason,
        "status": row.status,
        "date_started": row.date_started.isoformat(),
        "review_date": row.review_date.isoformat() if row.review_date else None,
        "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
        "outcome": row.outcome,
    }