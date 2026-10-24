"""Import the complete NeuroSync CSV bundle into the LMS database.

Run from ``backend``:
    python -m lms.csv_bundle_import path\\to\\dataset.zip --replace
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import uuid
import zipfile
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from lms.database import (
    CONFIGURED_LMS_DATABASE_URL,
    LMSBase,
    build_lms_session_factory,
    get_lms_database_url,
)
from lms.models import (
    ApprovedLeaveRecord,
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    AttendanceSession,
    DatasetImport,
    DatasetSourceRow,
    Intervention,
    Lecturer,
    LMSActivity,
    Module,
    ModuleEnrolment,
    MonthlyAttendanceSummary,
    Programme,
    Quiz,
    QuizAttempt,
    Referral,
    ResourceActivity,
    StaffMapping,
    Student,
    StudentMapping,
    Submission,
    WorkbookIntelligence,
)

BUNDLE_FILES = {
    "assessment_results.csv",
    "assessments.csv",
    "attendance.csv",
    "audit_logs.csv",
    "enrolments.csv",
    "interventions.csv",
    "leave_requests.csv",
    "lecturers.csv",
    "lms_activity.csv",
    "ml_features.csv",
    "modules.csv",
    "monthly_attendance.csv",
    "programmes.csv",
    "quiz_attempts.csv",
    "quizzes.csv",
    "referrals.csv",
    "resource_activity.csv",
    "sessions.csv",
    "students.csv",
    "study_activity.csv",
    "support_requests.csv",
    "user_accounts.csv",
    "wellbeing.csv",
}

SOURCE_ONLY_FILES = {
    "audit_logs.csv",
    "ml_features.csv",
    "study_activity.csv",
    "support_requests.csv",
    "students.csv",
    "user_accounts.csv",
    "wellbeing.csv",
}


def _read_csv(archive: zipfile.ZipFile, filename: str) -> list[dict[str, str]]:
    entry = archive.getinfo(filename)
    with archive.open(entry) as source:
        text = io.TextIOWrapper(source, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        if not reader.fieldnames:
            raise ValueError(f"{filename} has no CSV header row")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f"{filename} contains rows with more values than its header")
    return rows


def _required(row: dict[str, str], field: str, source: str) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"{source}.{field} is required")
    return value.strip()


def _optional(row: dict[str, str], field: str) -> str | None:
    value = row.get(field)
    return value.strip() if value and value.strip() else None


def _integer(row: dict[str, str], field: str, source: str, minimum: int = 0) -> int:
    value = _required(row, field, source)
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{source}.{field} must be an integer: {value!r}") from error
    if parsed < minimum:
        raise ValueError(f"{source}.{field} must be at least {minimum}")
    return parsed


def _number(row: dict[str, str], field: str, source: str, minimum: float | None = None, maximum: float | None = None) -> float:
    value = _required(row, field, source)
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValueError(f"{source}.{field} must be numeric: {value!r}") from error
    if (minimum is not None and parsed < minimum) or (maximum is not None and parsed > maximum):
        raise ValueError(f"{source}.{field} is outside the allowed range: {value!r}")
    return parsed


def _date(row: dict[str, str], field: str, source: str) -> date:
    try:
        return date.fromisoformat(_required(row, field, source)[:10])
    except ValueError as error:
        raise ValueError(f"{source}.{field} must be an ISO date") from error


def _datetime(row: dict[str, str], field: str, source: str) -> datetime:
    value = _required(row, field, source)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{source}.{field} must be an ISO timestamp") from error
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _validate_references(data: dict[str, list[dict[str, str]]]) -> None:
    def unique_values(filename: str, field: str) -> set[str]:
        values = [_required(row, field, filename) for row in data[filename]]
        if len(values) != len(set(values)):
            raise ValueError(f"{filename} contains duplicate {field} values")
        return set(values)

    student_ids = unique_values("students.csv", "student_id")
    lecturer_ids = unique_values("lecturers.csv", "lecturer_id")
    programme_ids = unique_values("programmes.csv", "programme_id")
    programme_names = unique_values("programmes.csv", "programme_name")
    module_ids = unique_values("modules.csv", "module_id")
    assessment_ids = unique_values("assessments.csv", "assessment_id")
    quiz_ids = unique_values("quizzes.csv", "quiz_id")
    session_ids = unique_values("sessions.csv", "session_id")
    referral_ids = unique_values("referrals.csv", "referral_id")
    student_emails = [_required(row, "student_email", "students.csv").lower() for row in data["students.csv"]]
    if len(student_emails) != len(set(student_emails)):
        raise ValueError("students.csv contains duplicate student_email values")
    for row in data["students.csv"]:
        if _required(row, "programme", "students.csv") not in programme_names:
            raise ValueError(f"students.csv references unknown programme {row['programme']!r}")

    def check(filename: str, field: str, allowed: set[str], optional: bool = False) -> None:
        for row in data[filename]:
            value = _optional(row, field) if optional else _required(row, field, filename)
            if value is not None and value not in allowed:
                raise ValueError(f"{filename}.{field} references unknown ID {value!r}")

    check("modules.csv", "programme_id", programme_ids)
    check("modules.csv", "lecturer_id", lecturer_ids)
    check("enrolments.csv", "student_id", student_ids)
    check("enrolments.csv", "module_id", module_ids)
    check("sessions.csv", "module_id", module_ids)
    check("attendance.csv", "student_id", student_ids)
    check("attendance.csv", "module_id", module_ids)
    check("attendance.csv", "session_id", session_ids, optional=True)
    check("assessments.csv", "module_id", module_ids)
    check("assessment_results.csv", "student_id", student_ids)
    check("assessment_results.csv", "assessment_id", assessment_ids)
    check("quiz_attempts.csv", "student_id", student_ids)
    check("quiz_attempts.csv", "quiz_id", quiz_ids)
    check("quizzes.csv", "module_id", module_ids)
    check("lms_activity.csv", "student_id", student_ids)
    check("lms_activity.csv", "module_id", module_ids, optional=True)
    check("resource_activity.csv", "student_id", student_ids)
    check("resource_activity.csv", "module_id", module_ids, optional=True)
    check("monthly_attendance.csv", "student_id", student_ids)
    check("leave_requests.csv", "student_id", student_ids)
    check("referrals.csv", "student_id", student_ids)
    check("referrals.csv", "lecturer_id", lecturer_ids)
    check("referrals.csv", "module_id", module_ids, optional=True)
    check("interventions.csv", "student_id", student_ids)
    check("interventions.csv", "referral_id", referral_ids)
    check("user_accounts.csv", "student_id", student_ids, optional=True)
    check("user_accounts.csv", "lecturer_id", lecturer_ids, optional=True)
    account_emails = [_required(row, "user_email", "user_accounts.csv").lower() for row in data["user_accounts.csv"]]
    if len(account_emails) != len(set(account_emails)):
        raise ValueError("user_accounts.csv contains duplicate user_email values")


def _read_bundle(path: Path) -> tuple[dict[str, list[dict[str, str]]], str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as archive:
        available = {Path(name).name for name in archive.namelist() if name.lower().endswith(".csv")}
        missing = BUNDLE_FILES - available
        if missing:
            raise ValueError(f"Dataset ZIP is missing CSV files: {', '.join(sorted(missing))}")
        data = {filename: _read_csv(archive, filename) for filename in BUNDLE_FILES}
    _validate_references(data)
    return data, digest


def import_csv_bundle(bundle_path: str, database_url: str, replace: bool = False) -> dict[str, Any]:
    source = Path(bundle_path).expanduser().resolve(strict=True)
    if not zipfile.is_zipfile(source):
        raise ValueError(f"Dataset bundle is not a valid ZIP file: {source}")
    data, digest = _read_bundle(source)
    engine, session_factory = build_lms_session_factory(database_url=database_url)
    try:
        db: Session = session_factory()
        try:
            LMSBase.metadata.create_all(bind=engine)
            has_existing_data = bool(db.query(Student).count() or db.query(DatasetImport).count())
            if has_existing_data and not replace:
                raise ValueError("LMS database is not empty; rerun with --replace to replace its dataset")
            if replace:
                db.rollback()
                db.close()
                LMSBase.metadata.drop_all(bind=engine)
                LMSBase.metadata.create_all(bind=engine)
                db = session_factory()

            programmes = {
                row["programme_id"]: Programme(
                    programme_id=row["programme_id"],
                    programme_code=row["programme_code"],
                    programme_name=row["programme_name"],
                    faculty=row["faculty"],
                    level=row["level"],
                )
                for row in data["programmes.csv"]
            }
            lecturers = {
                row["lecturer_id"]: Lecturer(
                    lecturer_id=row["lecturer_id"],
                    first_name=row["first_name"],
                    surname=row["surname"],
                    email=row["email"].lower(),
                    department=row["department"],
                )
                for row in data["lecturers.csv"]
            }
            db.add_all(programmes.values())
            db.add_all(lecturers.values())
            db.flush()

            students = {}
            for row in data["students.csv"]:
                student_id = row["student_id"]
                student = Student(
                    student_id=student_id,
                    first_name=row["first_name"],
                    surname=row["last_name"],
                    institutional_email=row["student_email"].lower(),
                    programme_id=next(
                        programme["programme_id"]
                        for programme in data["programmes.csv"]
                        if programme["programme_name"] == row["programme"]
                    ),
                    year_of_study=_integer(row, "year_of_study", "students.csv", 1),
                    semester=1,
                    behaviour_group=f"imported_{_slug(row['risk_band']).lower()}",
                    enrolment_status=_slug(row["enrolment_status"]),
                )
                students[student_id] = student
            db.add_all(students.values())

            modules = {
                row["module_id"]: Module(
                    module_id=row["module_id"],
                    programme_id=row["programme_id"],
                    module_code=row["module_code"],
                    module_name=row["module_name"],
                    credits=_integer(row, "credits", "modules.csv", 1),
                    semester=_integer(row, "semester", "modules.csv", 1),
                    lecturer_id=row["lecturer_id"],
                )
                for row in data["modules.csv"]
            }
            db.add_all(modules.values())
            db.flush()

            programme_by_name = {row["programme_name"]: row["programme_id"] for row in data["programmes.csv"]}
            db.add_all(
                ModuleEnrolment(
                    enrolment_id=row["enrolment_id"],
                    student_id=row["student_id"],
                    module_id=row["module_id"],
                    status=_slug(row["status"]),
                    enrolled_at=_datetime(row, "enrolled_at", "enrolments.csv"),
                )
                for row in data["enrolments.csv"]
            )
            assessments = {
                row["assessment_id"]: Assessment(
                    assessment_id=row["assessment_id"],
                    module_id=row["module_id"],
                    title=row["title"],
                    assessment_type=_slug(row["assessment_type"]),
                    weight=_number(row, "weight", "assessments.csv", 0),
                    maximum_mark=_number(row, "maximum_mark", "assessments.csv", 0.01),
                    due_date=_date(row, "due_date", "assessments.csv"),
                )
                for row in data["assessments.csv"]
            }
            db.add_all(assessments.values())
            quizzes = {
                row["quiz_id"]: Quiz(
                    quiz_id=row["quiz_id"],
                    module_id=row["module_id"],
                    title=row["title"],
                    available_date=_date(row, "available_date", "quizzes.csv"),
                    maximum_score=_number(row, "maximum_score", "quizzes.csv", 0.01),
                )
                for row in data["quizzes.csv"]
            }
            db.add_all(quizzes.values())
            db.add_all(
                AttendanceSession(
                    session_id=row["session_id"],
                    module_id=row["module_id"],
                    session_date=_date(row, "session_date", "sessions.csv"),
                    session_type=_slug(row["session_type"]),
                )
                for row in data["sessions.csv"]
            )
            db.flush()

            db.add_all(
                AttendanceRecord(
                    attendance_id=row["attendance_id"],
                    student_id=row["student_id"],
                    module_id=row["module_id"],
                    session_id=_optional(row, "session_id"),
                    session_date=_date(row, "session_date", "attendance.csv"),
                    status="EXCUSED" if _slug(row["status"]) == "APPROVED_LEAVE" else _slug(row["status"]),
                )
                for row in data["attendance.csv"]
            )
            db.add_all(
                AssessmentResult(
                    result_id=row["result_id"],
                    student_id=row["student_id"],
                    assessment_id=row["assessment_id"],
                    mark=_number(row, "mark", "assessment_results.csv", 0) if _optional(row, "mark") else None,
                    percentage=_number(row, "percentage", "assessment_results.csv", 0, 100) if _optional(row, "percentage") else None,
                    submission_date=_date(row, "submission_date", "assessment_results.csv") if _optional(row, "submission_date") else None,
                    status=_slug(row["status"]),
                )
                for row in data["assessment_results.csv"]
            )
            db.add_all(
                Submission(
                    submission_id=f"SUB-{row['result_id']}",
                    student_id=row["student_id"],
                    assessment_id=row["assessment_id"],
                    submitted_at=(
                        datetime.combine(_date(row, "submission_date", "assessment_results.csv"), time.min)
                        if _optional(row, "submission_date")
                        else None
                    ),
                    status=_slug(row["status"]),
                )
                for row in data["assessment_results.csv"]
            )
            db.add_all(
                QuizAttempt(
                    attempt_id=row["attempt_id"],
                    student_id=row["student_id"],
                    quiz_id=row["quiz_id"],
                    attempt_number=_integer(row, "attempt_number", "quiz_attempts.csv", 1),
                    score=_number(row, "score", "quiz_attempts.csv", 0),
                    percentage=_number(row, "percentage", "quiz_attempts.csv", 0, 100),
                    started_at=_datetime(row, "started_at", "quiz_attempts.csv"),
                    completed_at=_datetime(row, "completed_at", "quiz_attempts.csv") if _optional(row, "completed_at") else None,
                    duration=_integer(row, "duration_minutes", "quiz_attempts.csv"),
                )
                for row in data["quiz_attempts.csv"]
            )

            db.add_all(
                LMSActivity(
                    activity_id=row["activity_id"],
                    student_id=row["student_id"],
                    timestamp=_datetime(row, "timestamp", "lms_activity.csv"),
                    activity_type={
                        "CONTENT_VIEW": "VIEW_RESOURCE",
                        "ASSIGNMENT_VIEW": "VIEW_ASSESSMENT",
                        "DISCUSSION_POST": "DISCUSSION_POST",
                        "LOGIN": "LOGIN",
                    }.get(_slug(row["activity_type"]), _slug(row["activity_type"])),
                    module_id=_optional(row, "module_id"),
                    session_duration=_integer(row, "session_duration", "lms_activity.csv"),
                )
                for row in data["lms_activity.csv"]
            )
            db.add_all(
                ResourceActivity(
                    resource_activity_id=row["resource_activity_id"],
                    student_id=row["student_id"],
                    timestamp=_datetime(row, "timestamp", "resource_activity.csv"),
                    activity_type={
                        "VIEW": "VIEW_RESOURCE",
                        "DOWNLOAD": "DOWNLOAD_RESOURCE",
                        "REPLAY": "VIEW_RESOURCE",
                    }.get(_slug(row["activity_type"]), _slug(row["activity_type"])),
                    module_id=_optional(row, "module_id"),
                    resource_name=_optional(row, "resource_name"),
                )
                for row in data["resource_activity.csv"]
            )
            db.add_all(
                MonthlyAttendanceSummary(
                    summary_id=f"SUM-{row['student_id']}-{row['month'].replace('-', '')}",
                    student_id=row["student_id"],
                    month=row["month"],
                    scheduled_sessions=_integer(row, "scheduled_sessions", "monthly_attendance.csv"),
                    attended_sessions=_integer(row, "attended_sessions", "monthly_attendance.csv"),
                    approved_leave_sessions=_integer(row, "approved_leave_sessions", "monthly_attendance.csv"),
                    unexcused_absences=_integer(row, "unexcused_absences", "monthly_attendance.csv"),
                    attendance_percentage=_number(row, "attendance_pct_excluding_leave", "monthly_attendance.csv", 0, 100),
                    source=source.name,
                )
                for row in data["monthly_attendance.csv"]
            )
            db.add_all(
                ApprovedLeaveRecord(
                    leave_id=row["leave_id"],
                    student_id=row["student_id"],
                    month=row["month"],
                    sessions=_integer(row, "approved_leave_sessions", "leave_requests.csv", 1),
                    reason=_optional(row, "reason"),
                    approval_status=_slug(row["approval_status"]),
                    source=source.name,
                )
                for row in data["leave_requests.csv"]
            )
            referrals = {
                row["referral_id"]: Referral(
                    referral_id=row["referral_id"],
                    student_id=row["student_id"],
                    lecturer_id=row["lecturer_id"],
                    advisor_user_id=_optional(row, "advisor_user_id"),
                    module_id=_optional(row, "module_id"),
                    risk_level=_slug(row["risk_level"]),
                    risk_score=_number(row, "risk_score", "referrals.csv", 0, 100),
                    reason=row["reason"],
                    lecturer_notes=_optional(row, "lecturer_notes"),
                    urgency="PRIORITY" if _slug(row["urgency"]) == "HIGH" else "STANDARD",
                    status="UNDER_REVIEW" if _slug(row["status"]) == "IN_PROGRESS" else _slug(row["status"]),
                    created_at=_datetime(row, "created_at", "referrals.csv"),
                    updated_at=_datetime(row, "created_at", "referrals.csv"),
                )
                for row in data["referrals.csv"]
            }
            db.add_all(referrals.values())
            db.add_all(
                Intervention(
                    intervention_id=row["intervention_id"],
                    referral_id=row["referral_id"],
                    student_id=row["student_id"],
                    advisor_user_id=row["advisor_user_id"],
                    strategy=row["strategy"],
                    reason=row["reason"],
                    advisor_notes=_optional(row, "advisor_notes"),
                    date_started=datetime.combine(_date(row, "date_started", "interventions.csv"), time.min),
                    review_date=_date(row, "review_date", "interventions.csv") if _optional(row, "review_date") else None,
                    follow_up_date=_date(row, "follow_up_date", "interventions.csv") if _optional(row, "follow_up_date") else None,
                    outcome=_optional(row, "outcome"),
                    status="ACTIVE" if _slug(row["status"]) == "OPEN" else _slug(row["status"]),
                )
                for row in data["interventions.csv"]
            )

            accounts_by_email = {
                _required(row, "user_email", "user_accounts.csv").lower(): row
                for row in data["user_accounts.csv"]
            }
            db.add_all(
                StudentMapping(app_user_email=email, student_id=row["student_id"])
                for email, row in accounts_by_email.items()
                if _slug(row["role"]) == "STUDENT" and _optional(row, "student_id")
            )
            db.add_all(
                StaffMapping(app_user_email=email, lecturer_id=row["lecturer_id"])
                for email, row in accounts_by_email.items()
                if _slug(row["role"]) == "LECTURER" and _optional(row, "lecturer_id")
            )

            for filename in sorted(SOURCE_ONLY_FILES):
                stem = Path(filename).stem
                rows = data[filename]
                for index, row in enumerate(rows, start=2):
                    row_id = next(
                        (value for key, value in row.items() if key.endswith("_id") and value),
                        f"{stem}-{index}",
                    )
                    payload = json.dumps(row, ensure_ascii=True, sort_keys=True)
                    db.add(DatasetSourceRow(
                        source_row_id=f"{stem}:{row_id}",
                        source_name=filename,
                        row_number=index,
                        payload=payload,
                    ))
                    db.add(WorkbookIntelligence(
                        record_id=f"CSV-{stem.upper()}-{index}",
                        sheet_name=stem,
                        row_number=index,
                        payload=payload,
                    ))

            manifest = DatasetImport(
                import_id=f"IMP-{uuid.uuid4().hex[:12].upper()}",
                source_name=source.name,
                content_sha256=digest,
                student_count=len(students),
                attendance_count=len(data["attendance.csv"]),
                assessment_count=len(data["assessment_results.csv"]),
                leave_count=len(data["leave_requests.csv"]),
            )
            db.add(manifest)
            db.commit()
            return {
                "status": "imported",
                "student_count": len(students),
                "programme_count": len(programmes),
                "lecturer_count": len(lecturers),
                "module_count": len(modules),
                "attendance_count": len(data["attendance.csv"]),
                "assessment_result_count": len(data["assessment_results.csv"]),
                "lms_activity_count": len(data["lms_activity.csv"]),
                "referral_count": len(referrals),
                "source_only_rows": sum(len(data[name]) for name in SOURCE_ONLY_FILES),
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all CSVs in the NeuroSync dataset ZIP into the LMS database.")
    parser.add_argument("bundle", help="Path to NeuroSync dataset ZIP")
    parser.add_argument(
        "--database-url",
        default=CONFIGURED_LMS_DATABASE_URL or get_lms_database_url(),
        help="Target LMS database URL; defaults to the configured LMS database.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the current LMS dataset. Without this flag, non-empty databases are left untouched.",
    )
    args = parser.parse_args()
    print(import_csv_bundle(args.bundle, args.database_url, replace=args.replace))


if __name__ == "__main__":
    main()
