import csv
import io
import zipfile

from lms.csv_bundle_import import BUNDLE_FILES, import_csv_bundle
from lms.database import build_lms_session_factory
from lms.features import extract_student_features
from lms.models import (
    AssessmentResult,
    DatasetSourceRow,
    LMSActivity,
    MonthlyAttendanceSummary,
    StaffMapping,
    Student,
    StudentMapping,
)


def _write_bundle(path):
    rows = {
        "assessment_results.csv": [
            {"result_id": "RE0001", "student_id": "ST0001", "assessment_id": "AS0001", "mark": "80", "percentage": "80", "submission_date": "2026-03-10", "status": "Submitted"},
            {"result_id": "RE0002", "student_id": "ST0001", "assessment_id": "AS0001", "mark": "", "percentage": "", "submission_date": "", "status": "Missing"},
        ],
        "assessments.csv": [{"assessment_id": "AS0001", "module_id": "M001", "title": "Assignment", "assessment_type": "Assignment", "weight": "100", "maximum_mark": "100", "due_date": "2026-03-10"}],
        "attendance.csv": [{"attendance_id": "AT0001", "student_id": "ST0001", "module_id": "M001", "session_id": "S001", "session_date": "2026-03-10", "status": "Present"}],
        "audit_logs.csv": [{"event_id": "EV0001", "actor_id": "ST0001", "actor_reference": "Student", "action": "LOGIN", "outcome": "Success", "request_id": "RQ0001", "source_ip": "192.0.2.1", "occurred_at": "2026-03-10T09:00:00"}],
        "enrolments.csv": [{"enrolment_id": "EN0001", "student_id": "ST0001", "module_id": "M001", "status": "Enrolled", "enrolled_at": "2026-01-01T09:00:00"}],
        "interventions.csv": [{"intervention_id": "IV0001", "referral_id": "RF0001", "student_id": "ST0001", "advisor_user_id": "ADV001", "strategy": "Study plan", "reason": "Academic support", "advisor_notes": "Follow up", "date_started": "2026-03-11", "review_date": "2026-04-11", "follow_up_date": "2026-04-18", "outcome": "Pending review", "status": "Open"}],
        "leave_requests.csv": [{"leave_id": "LV0001", "student_id": "ST0001", "month": "2026-03", "approved_leave_sessions": "1", "reason": "Personal", "approval_status": "Approved"}],
        "lecturers.csv": [{"lecturer_id": "L001", "first_name": "Lee", "surname": "Lecturer", "email": "lecturer@demo.test", "department": "Computing"}],
        "lms_activity.csv": [{"activity_id": "LA0001", "student_id": "ST0001", "timestamp": "2026-03-10T09:00:00", "activity_type": "Login", "module_id": "M001", "session_duration": "10"}],
        "ml_features.csv": [{"student_id": "ST0001", "academic_average": "80", "assignment_completion": "100", "failed_module_count": "0", "attendance_percentage": "100", "attendance_change": "0", "study_hours_weekly": "5", "lms_activity_score": "70", "mood_average": "8", "stress_average": "4", "risk_score": "10", "risk_level": "Low"}],
        "modules.csv": [{"module_id": "M001", "programme_id": "P001", "module_code": "CS101", "module_name": "Computing", "credits": "20", "semester": "1", "lecturer_id": "L001"}],
        "monthly_attendance.csv": [{"student_id": "ST0001", "month": "2026-03", "scheduled_sessions": "4", "attended_sessions": "3", "approved_leave_sessions": "1", "unexcused_absences": "0", "attendance_pct_excluding_leave": "100", "leave_reason": "Personal"}],
        "programmes.csv": [{"programme_id": "P001", "programme_code": "CS", "programme_name": "Computing", "faculty": "Science", "level": "Undergraduate"}],
        "quiz_attempts.csv": [{"attempt_id": "QA0001", "student_id": "ST0001", "quiz_id": "Q001", "attempt_number": "1", "score": "8", "percentage": "80", "started_at": "2026-03-10T09:00:00", "completed_at": "2026-03-10T09:10:00", "duration_minutes": "10"}],
        "quizzes.csv": [{"quiz_id": "Q001", "module_id": "M001", "title": "Quiz", "available_date": "2026-03-10", "maximum_score": "10"}],
        "referrals.csv": [{"referral_id": "RF0001", "student_id": "ST0001", "lecturer_id": "L001", "advisor_user_id": "ADV001", "module_id": "M001", "risk_level": "High", "risk_score": "75", "reason": "Attendance and assessment concern", "lecturer_notes": "Please review", "urgency": "High", "status": "In Progress", "created_at": "2026-03-11T09:00:00"}],
        "resource_activity.csv": [{"resource_activity_id": "RA0001", "student_id": "ST0001", "timestamp": "2026-03-10T09:00:00", "activity_type": "View", "module_id": "M001", "resource_name": "slides.pdf"}],
        "sessions.csv": [{"session_id": "S001", "module_id": "M001", "session_date": "2026-03-10", "session_type": "Lecture"}],
        "students.csv": [{"student_id": "ST0001", "first_name": "Sam", "last_name": "Student", "student_email": "student@demo.test", "phone_number": "+27000000001", "faculty": "Science", "programme": "Computing", "year_of_study": "1", "enrolment_status": "Active", "advisor_id": "ADV001", "overall_attendance_pct": "100", "average_mark_pct": "80", "tasks_completed": "1", "tasks_missing": "1", "risk_band": "Low"}],
        "study_activity.csv": [{"study_id": "SA0001", "student_id": "ST0001", "subject": "M001", "duration_minutes": "40", "activity_type": "Self Study", "created_at": "2026-03-10T09:00:00"}],
        "support_requests.csv": [{"request_id": "SR0001", "student_id": "ST0001", "request_type": "Academic", "message": "Need support", "status": "Open", "created_at": "2026-03-10T09:00:00"}],
        "user_accounts.csv": [
            {"user_email": "student@demo.test", "name": "Sam Student", "role": "Student", "student_id": "ST0001", "lecturer_id": "", "account_status": "Active"},
            {"user_email": "lecturer@demo.test", "name": "Lee Lecturer", "role": "Lecturer", "student_id": "", "lecturer_id": "L001", "account_status": "Active"},
            {"user_email": "advisor@demo.test", "name": "Faculty Advisor", "role": "Advisor", "student_id": "", "lecturer_id": "", "account_status": "Active"},
        ],
        "wellbeing.csv": [{"wellbeing_id": "WB0001", "student_id": "ST0001", "mood_score": "8", "stress_level": "4", "notes": "Check-in", "created_at": "2026-03-10T09:00:00"}],
    }
    assert set(rows) == BUNDLE_FILES
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, records in rows.items():
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
            archive.writestr(filename, stream.getvalue())
    return path


def test_csv_bundle_import_preserves_all_records_and_null_missing_marks(tmp_path):
    bundle = _write_bundle(tmp_path / "dataset.zip")
    database_url = f"sqlite:///{tmp_path / 'imported.db'}"

    result = import_csv_bundle(str(bundle), database_url)
    engine, factory = build_lms_session_factory(database_url=database_url)
    db = factory()
    try:
        assert result["student_count"] == 1
        assert result["attendance_count"] == 1
        assert result["source_only_rows"] == 9
        assert db.query(Student).count() == 1
        assert db.query(MonthlyAttendanceSummary).count() == 1
        assert db.query(LMSActivity).filter_by(activity_type="LOGIN").count() == 1
        assert db.query(StudentMapping).filter_by(student_id="ST0001").count() == 1
        assert db.query(StaffMapping).filter_by(lecturer_id="L001").count() == 1
        assert db.query(DatasetSourceRow).filter_by(source_name="students.csv").count() == 1
        missing = db.query(AssessmentResult).filter_by(result_id="RE0002").one()
        assert missing.mark is None
        assert missing.percentage is None
        assert extract_student_features(db, "ST0001")["assessment_average"] == 80
    finally:
        db.close()
        engine.dispose()
