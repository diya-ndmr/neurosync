"""Import the bundled synthetic NeuroSync CSV pack into the LMS and app databases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import secrets
import zipfile
from collections import defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import Base, SessionLocal, engine as app_engine
from app.models import (
    Assessment as AppAssessment,
    Attendance as AppAttendance,
    ClassAttendanceRecord,
    ImportedDatasetState,
    LearningProgress,
    LearningResource,
    LearningTopic,
    Module as AppModule,
    MoodCheckin,
    Recommendation,
    RiskPrediction,
    StudentProfile,
    StudySession,
    TopicFeedback,
    UserPreference,
    WellnessAppointment,
    WellnessAppointmentSlot,
    WellnessReferral,
)
from app.models.support_request import SupportRequest
from app.models.user import User, UserRole
from app.services.authentication_service import hash_password
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
    Referral,
    ResourceActivity,
    StaffMapping,
    Student,
    StudentMapping,
    Submission,
    WorkbookIntelligence,
)

DATASET_ID = "neurosync-complete-csv-data-pack"
LEGACY_DEMO_STUDENT_COUNT = 6
DEFAULT_BUNDLE = Path(__file__).resolve().parents[1] / "datasets" / "NeuroSync_Complete_CSV_Data_Pack.zip"
PACK_DIRECTORY = "NeuroSync_Complete_CSV_Data_Pack/"
PACK_FILES = {
    "advisor_assignments.csv",
    "assessments.csv",
    "attendance_records.csv",
    "interventions.csv",
    "learning_resources.csv",
    "lecturer_feedback.csv",
    "login_activity.csv",
    "master_student_snapshot.csv",
    "module_topics.csv",
    "modules.csv",
    "notifications.csv",
    "referrals.csv",
    "risk_assessments.csv",
    "student_module_enrolments.csv",
    "student_preferences.csv",
    "students.csv",
    "topic_performance.csv",
    "users_roles.csv",
    "wellness_bookings.csv",
    "wellness_slots.csv",
}
ROLE_MAP = {
    "student": UserRole.student,
    "lecturer": UserRole.lecturer,
    "advisor": UserRole.advisor,
    "admin": UserRole.admin,
}
SUPPORTED_RESOURCE_SCHEMES = {"http", "https"}


def _read_pack(path: Path) -> tuple[dict[str, list[dict[str, str]]], str]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as archive:
        entries: dict[str, str] = {}
        for name in archive.namelist():
            if not name.lower().endswith(".csv"):
                continue
            filename = Path(name.replace("\\", "/")).name
            if filename in PACK_FILES:
                if filename in entries:
                    raise ValueError(f"Dataset ZIP contains duplicate {filename}")
                entries[filename] = name
        missing = PACK_FILES - set(entries)
        if missing:
            raise ValueError(f"Dataset ZIP is missing CSV files: {', '.join(sorted(missing))}")

        result: dict[str, list[dict[str, str]]] = {}
        for filename, member in entries.items():
            with archive.open(member) as source:
                reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError(f"{filename} has missing or duplicate CSV headers")
                rows = list(reader)
            if not rows or any(None in row for row in rows):
                raise ValueError(f"{filename} contains no rows or a row with extra values")
            if "data_is_synthetic" in rows[0] and any(
                row.get("data_is_synthetic", "").strip().lower() != "true" for row in rows
            ):
                raise ValueError(f"{filename} contains a row not marked as synthetic")
            result[filename] = rows
    _validate_pack(result)
    return result, digest


def _required(row: dict[str, str], field: str, source: str) -> str:
    value = row.get(field)
    if value is None or not value.strip():
        raise ValueError(f"{source}.{field} is required")
    return value.strip()


def _optional(row: dict[str, str], field: str) -> Optional[str]:
    value = row.get(field)
    return value.strip() if value and value.strip() else None


def _date(value: str, source: str) -> date:
    try:
        return date.fromisoformat(value[:10])
    except ValueError as error:
        raise ValueError(f"{source} must be an ISO date") from error


def _datetime(value: str, source: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{source} must be an ISO timestamp") from error
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _number(value: str, source: str, minimum: float = 0, maximum: Optional[float] = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{source} must be numeric") from error
    if result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{source} is outside the allowed range")
    return result


def _integer(value: str, source: str, minimum: int = 0) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{source} must be an integer") from error
    if result < minimum:
        raise ValueError(f"{source} must be at least {minimum}")
    return result


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _validate_pack(data: dict[str, list[dict[str, str]]]) -> None:
    def unique(filename: str, field: str) -> set[str]:
        values = [_required(row, field, filename) for row in data[filename]]
        if len(values) != len(set(values)):
            raise ValueError(f"{filename} contains duplicate {field} values")
        return set(values)

    students = unique("students.csv", "student_id")
    modules = unique("modules.csv", "module_id")
    users = unique("users_roles.csv", "user_id")
    topics = unique("module_topics.csv", "topic_id")
    referrals = unique("referrals.csv", "referral_id")
    slots = unique("wellness_slots.csv", "slot_id")
    emails = [_required(row, "email", "users_roles.csv").lower() for row in data["users_roles.csv"]]
    if len(emails) != len(set(emails)):
        raise ValueError("users_roles.csv contains duplicate email values")

    student_emails = {row["student_id"]: row["email"].lower() for row in data["students.csv"]}
    account_by_id = {row["user_id"]: row for row in data["users_roles.csv"]}
    for student_id, email in student_emails.items():
        account = account_by_id.get(student_id)
        if account is None or account["role"].lower() != "student" or account["email"].lower() != email:
            raise ValueError(f"Student account mapping is invalid for {student_id}")

    for filename, field, valid in (
        ("modules.csv", "lecturer_id", users),
        ("module_topics.csv", "module_id", modules),
        ("student_module_enrolments.csv", "student_id", students),
        ("student_module_enrolments.csv", "module_id", modules),
        ("attendance_records.csv", "student_id", students),
        ("attendance_records.csv", "module_id", modules),
        ("assessments.csv", "student_id", students),
        ("assessments.csv", "module_id", modules),
        ("assessments.csv", "topic_id", topics),
        ("topic_performance.csv", "student_id", students),
        ("topic_performance.csv", "module_id", modules),
        ("topic_performance.csv", "topic_id", topics),
        ("lecturer_feedback.csv", "student_id", students),
        ("lecturer_feedback.csv", "module_id", modules),
        ("lecturer_feedback.csv", "topic_id", topics),
        ("lecturer_feedback.csv", "lecturer_id", users),
        ("learning_resources.csv", "module_id", modules),
        ("learning_resources.csv", "topic_id", topics),
        ("risk_assessments.csv", "student_id", students),
        ("referrals.csv", "student_id", students),
        ("referrals.csv", "assigned_advisor_id", users),
        ("interventions.csv", "student_id", students),
        ("interventions.csv", "referral_id", referrals),
        ("interventions.csv", "advisor_id", users),
        ("wellness_slots.csv", "staff_id", users),
        ("wellness_bookings.csv", "student_id", students),
        ("wellness_bookings.csv", "slot_id", slots),
        ("wellness_bookings.csv", "referral_id", referrals),
    ):
        for row in data[filename]:
            value = _optional(row, field)
            if value is not None and value not in valid:
                raise ValueError(f"{filename}.{field} references unknown ID {value!r}")
    for row in data["learning_resources.csv"]:
        student_id = _optional(row, "assigned_to_student_id")
        if student_id is not None and student_id not in students:
            raise ValueError("learning_resources.csv references an unknown assigned student")
        url = _required(row, "resource_url", "learning_resources.csv")
        if urlparse(url).scheme.lower() not in SUPPORTED_RESOURCE_SCHEMES:
            raise ValueError("learning_resources.csv contains an unsupported resource URL")
    for filename, id_field in (
        ("attendance_records.csv", "attendance_id"),
        ("assessments.csv", "assessment_id"),
        ("lecturer_feedback.csv", "feedback_id"),
        ("learning_resources.csv", "resource_id"),
        ("interventions.csv", "intervention_id"),
        ("login_activity.csv", "login_event_id"),
        ("notifications.csv", "notification_id"),
        ("risk_assessments.csv", "risk_record_id"),
        ("wellness_bookings.csv", "booking_id"),
    ):
        unique(filename, id_field)
    for row in data["wellness_bookings.csv"]:
        if row.get("student_consent_recorded", "").strip().lower() != "true":
            raise ValueError("wellness_bookings.csv contains a booking without recorded consent")


def _insert_batches(db: Session, values: Iterable[Any], batch_size: int = 2000) -> None:
    batch = []
    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            model = type(batch[0])
            db.flush()
            db.bulk_insert_mappings(
                model,
                [
                    {key: field for key, field in record.__dict__.items() if not key.startswith("_")}
                    for record in batch
                ],
            )
            db.flush()
            batch.clear()
    if batch:
        model = type(batch[0])
        db.flush()
        db.bulk_insert_mappings(
            model,
            [
                {key: field for key, field in record.__dict__.items() if not key.startswith("_")}
                for record in batch
            ],
        )
        db.flush()


def _source_identifier(filename: str, row: dict[str, str], index: int) -> str:
    if filename == "topic_performance.csv":
        return f"{row['student_id']}:{row['topic_id']}"
    if filename == "student_module_enrolments.csv":
        return f"{row['student_id']}:{row['module_id']}"
    if filename == "advisor_assignments.csv":
        return f"{row['student_id']}:{row['advisor_id']}"
    if filename in ("student_preferences.csv", "master_student_snapshot.csv"):
        return row["student_id"]
    for key in row:
        if key.endswith("_id") and key != "student_id" and row[key].strip():
            return row[key].strip()
    if row.get("student_id"):
        return row["student_id"]
    return f"row-{index}"


def _source_payload(filename: str, row: dict[str, str]) -> str:
    sanitized = dict(row)
    if filename == "users_roles.csv":
        sanitized.pop("password_hash_demo", None)
    if filename == "wellness_bookings.csv":
        sanitized.pop("confidentiality_note", None)
    return json.dumps(sanitized, ensure_ascii=True, sort_keys=True)


def _ensure_resource_columns(database_engine) -> None:
    inspector = inspect(database_engine)
    if "learning_resources" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("learning_resources")}
    additions = {
        "assigned_student_id": "VARCHAR REFERENCES students(id)",
        "provider": "VARCHAR NOT NULL DEFAULT 'lecturer'",
        "reviewed_by_lecturer": "BOOLEAN NOT NULL DEFAULT 1",
        "recommended_reason": "TEXT",
        "display_priority": "INTEGER NOT NULL DEFAULT 0",
    }
    with database_engine.begin() as connection:
        for name, declaration in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE learning_resources ADD COLUMN {name} {declaration}"))


def _app_delete_old_dataset(db: Session) -> None:
    for model in (
        ClassAttendanceRecord,
        LearningProgress,
        LearningResource,
        TopicFeedback,
        LearningTopic,
        WellnessAppointment,
        WellnessReferral,
        WellnessAppointmentSlot,
        UserPreference,
        SupportRequest,
        Recommendation,
        RiskPrediction,
        MoodCheckin,
        StudySession,
        AppAssessment,
        AppAttendance,
        StudentProfile,
        AppModule,
    ):
        db.query(model).delete(synchronize_session=False)
    db.flush()


def _prepare_app_users(
    db: Session,
    data: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str], dict[str, str]]:
    users_by_id = {row["user_id"]: row for row in data["users_roles.csv"]}
    students_by_id = {row["student_id"]: row for row in data["students.csv"]}
    modules = data["modules.csv"]
    lecturer_ids = sorted({row["lecturer_id"] for row in modules})
    advisor_ids = sorted({
        row["advisor_id"] for row in data["advisor_assignments.csv"]
    })
    if not lecturer_ids or not advisor_ids:
        raise ValueError("Dataset requires at least one lecturer and advisor")

    old_students = db.query(StudentProfile).order_by(StudentProfile.student_number).all()
    legacy_student_users = [profile.user for profile in old_students[:LEGACY_DEMO_STUDENT_COUNT]]
    legacy_student_users = [user for user in legacy_student_users if user is not None]
    old_lecturer = db.query(User).filter(User.role == UserRole.lecturer).order_by(User.created_at).first()
    old_advisor = db.query(User).filter(User.role == UserRole.advisor).order_by(User.created_at).first()
    old_admin = db.query(User).filter(User.role == UserRole.admin).order_by(User.created_at).first()

    assigned: dict[str, User] = {}
    for user, student_id in zip(
        legacy_student_users,
        sorted(students_by_id)[:len(legacy_student_users)],
    ):
        record = users_by_id.get(student_id)
        if record is None:
            continue
        user.email = record["email"].lower()
        user.name = students_by_id[student_id]["full_name"]
        user.role = UserRole.student
        assigned[record["user_id"]] = user

    role_aliases = (
        (old_lecturer, lecturer_ids[0]),
        (old_advisor, advisor_ids[0]),
        (
            old_admin,
            next(row["user_id"] for row in data["users_roles.csv"] if row["role"].lower() == "admin"),
        ),
    )
    for existing_user, source_user_id in role_aliases:
        record = users_by_id.get(source_user_id)
        if existing_user is not None and record is not None:
            existing_user.email = record["email"].lower()
            existing_user.name = record["display_name"]
            assigned[source_user_id] = existing_user

    db.flush()
    known_by_email = {user.email.lower(): user for user in db.query(User).all()}
    id_to_app_id: dict[str, str] = {}
    app_users_by_id: dict[str, str] = {}
    for source_user_id, record in users_by_id.items():
        role = record["role"].strip().lower()
        if role not in ROLE_MAP:
            continue
        user = assigned.get(source_user_id) or known_by_email.get(record["email"].lower())
        if user is None:
            requested_id = source_user_id
            if db.query(User.id).filter(User.id == requested_id).first():
                requested_id = f"dataset-{source_user_id}"
            user = User(
                id=requested_id,
                email=record["email"].lower(),
                name=record["display_name"],
                password_hash=hash_password(secrets.token_urlsafe(48)),
                role=ROLE_MAP[role],
            )
            db.add(user)
        else:
            user.email = record["email"].lower()
            user.name = record["display_name"]
            user.role = ROLE_MAP[role]
        id_to_app_id[source_user_id] = user.id
        app_users_by_id[source_user_id] = user.id
        known_by_email[record["email"].lower()] = user
    db.flush()
    return id_to_app_id, app_users_by_id


def _reset_app_database(
    data: dict[str, list[dict[str, str]]],
    digest: str,
    app_database_engine,
    app_session_factory: sessionmaker,
    replace: bool,
) -> dict[str, str]:
    Base.metadata.create_all(bind=app_database_engine)
    _ensure_resource_columns(app_database_engine)
    db = app_session_factory()
    try:
        state = db.query(ImportedDatasetState).filter(
            ImportedDatasetState.dataset_id == DATASET_ID
        ).first()
        if state is not None and not replace:
            if state.content_sha256 != digest:
                raise ValueError(
                    "App database already contains a different imported dataset; use --replace to replace it"
                )
            user_ids = {
                row["user_id"]: row["email"].lower()
                for row in data["users_roles.csv"] if row["role"].lower() in ROLE_MAP
            }
            existing = {row.email.lower(): row.id for row in db.query(User).all()}
            mapping = {
                source_id: existing[email]
                for source_id, email in user_ids.items()
                if email in existing
            }
            if len(mapping) != len(user_ids):
                raise ValueError("Imported app accounts are incomplete; use --replace to rebuild the demo dataset")
            return mapping
        if state is None and not replace and any(
            db.query(model).count()
            for model in (StudentProfile, AppModule, ClassAttendanceRecord, LearningTopic)
        ):
            raise ValueError("App database already contains data; use --replace to replace the demo dataset")
        id_to_app_id, app_users_by_id = _prepare_app_users(db, data)
        _app_delete_old_dataset(db)

        students = data["students.csv"]
        student_profiles = []
        for row in students:
            source_user_id = row["student_id"]
            app_user_id = id_to_app_id.get(source_user_id)
            if app_user_id is None:
                raise ValueError(f"No login identity was mapped to {source_user_id}")
            student_profiles.append(StudentProfile(
                id=row["student_id"],
                user_id=app_user_id,
                student_number=row["student_id"],
                first_name=row["first_name"],
                surname=row["last_name"],
                programme=row["programme"],
                year_level=_integer(row["year_of_study"], "students.year_of_study", 1),
            ))
        _insert_batches(db, student_profiles)

        modules = data["modules.csv"]
        module_by_id = {row["module_id"]: row for row in modules}
        db.add_all(AppModule(
            id=row["module_id"],
            module_code=row["module_id"],
            module_name=row["module_name"],
            faculty=row["faculty"],
        ) for row in modules)
        db.flush()

        db.add_all(LearningTopic(
            id=row["topic_id"],
            module_id=row["module_id"],
            name=row["topic_name"],
        ) for row in data["module_topics.csv"])
        db.flush()

        _insert_batches(db, (
            AppAttendance(
                id=row["attendance_id"],
                student_id=row["student_id"],
                module_id=row["module_id"],
                attendance_percentage=100.0 if row["attendance_status"].strip().lower() in ("present", "late") else 0.0,
                date=_date(row["class_date"], "attendance_records.class_date"),
            )
            for row in data["attendance_records.csv"]
            if row["attendance_status"].strip().lower() != "approved leave"
        ))
        _insert_batches(db, (
            ClassAttendanceRecord(
                id=row["attendance_id"],
                student_id=row["student_id"],
                module_id=row["module_id"],
                class_name="Class session",
                class_date=_date(row["class_date"], "attendance_records.class_date"),
                status={
                    "present": "present",
                    "late": "late",
                    "absent": "absent",
                    "approved leave": "approved_leave",
                    "excused": "excused",
                }.get(row["attendance_status"].strip().lower(), "absent"),
                updated_by=id_to_app_id.get(row["recorded_by"], app_users_by_id[next(
                    item["user_id"] for item in data["users_roles.csv"] if item["role"].lower() == "admin"
                )]),
            )
            for row in data["attendance_records.csv"]
        ))
        _insert_batches(db, (
            AppAssessment(
                id=row["assessment_id"],
                student_id=row["student_id"],
                module_id=row["module_id"],
                assessment_type=row["assessment_type"],
                mark=_number(row["score_percent"], "assessments.score_percent", 0, 100),
                assessment_date=_date(row["assessment_date"], "assessments.assessment_date"),
                title=row.get("assessment_title"),
                max_score=_number(row["max_score"], "assessments.max_score", 0.01),
                status=row.get("submission_status"),
                feedback=row.get("feedback_summary"),
                topic_name=row.get("topic_name"),
            )
            for row in data["assessments.csv"]
        ))

        _insert_batches(db, (
            TopicFeedback(
                id=row["feedback_id"],
                topic_id=row["topic_id"],
                student_id=row["student_id"],
                lecturer_id=id_to_app_id[row["lecturer_id"]],
                strengths=[],
                learning_gaps=[row["topic_name"]] if row["understanding_level"].strip().lower() == "needs support" else [],
                feedback=row["feedback_text"],
                learning_goal=row["next_step"],
                created_at=datetime.combine(_date(row["feedback_date"], "lecturer_feedback.feedback_date"), time.min),
            )
            for row in data["lecturer_feedback.csv"]
        ))

        resource_rows = data["learning_resources.csv"]
        _insert_batches(db, (
            LearningResource(
                id=row["resource_id"],
                topic_id=row["topic_id"],
                uploaded_by=id_to_app_id[module_by_id[row["module_id"]]["lecturer_id"]],
                assigned_student_id=_optional(row, "assigned_to_student_id"),
                title=row["resource_title"],
                description=row["recommended_reason"],
                resource_type="link",
                resource_url=row["resource_url"],
                provider=row["provided_by"].strip(),
                reviewed_by_lecturer=row["reviewed_by_lecturer"].strip().lower() == "true",
                recommended_reason=row["recommended_reason"],
                display_priority=2 if row["provided_by"].strip().lower() == "lecturer" else 1,
                created_at=datetime.combine(_date(row["assigned_date"], "learning_resources.assigned_date"), time.min),
            )
            for row in resource_rows
        ))
        _insert_batches(db, (
            LearningProgress(
                student_id=row["assigned_to_student_id"],
                resource_id=row["resource_id"],
                status="completed" if row["completion_status"].strip().lower() == "completed" else "viewed",
                updated_at=datetime.combine(_date(row["assigned_date"], "learning_resources.assigned_date"), time.min),
            )
            for row in resource_rows
            if row["completion_status"].strip().lower() in ("completed", "in progress")
        ))

        for user_row in data["users_roles.csv"]:
            if user_row["role"].lower() != "student":
                continue
            preference = next((
                row for row in data["student_preferences.csv"]
                if row["student_id"] == user_row["user_id"]
            ), None)
            if preference is None:
                continue
            accent = preference["accent_colour"].strip().lower()
            if accent not in ("blue", "purple", "green", "neutral"):
                accent = "blue"
            theme = preference["theme"].strip().lower()
            if theme not in ("light", "dark", "system"):
                theme = "light"
            layout = preference["dashboard_layout"].strip().lower()
            if layout not in ("comfortable", "compact"):
                layout = "comfortable"
            text_size = preference["text_size"].strip().lower()
            db.add(UserPreference(
                user_id=id_to_app_id[user_row["user_id"]],
                settings={
                    "theme": theme,
                    "accent": accent,
                    "layout": layout,
                    "study_reminders": preference["study_reminders_enabled"].strip().lower() == "true",
                    "weekly_summary": preference["weekly_summary_enabled"].strip().lower() == "true",
                    "reminder_frequency": "weekly",
                    "text_size": "large" if text_size == "large" else "default",
                    "dashboard_order": [],
                    "preferred_study_start": preference["preferred_study_start"].strip() or "18:00",
                    "timezone": preference["timezone"].strip() or "Africa/Johannesburg",
                },
            ))

        snapshot_rows = {row["student_id"]: row for row in data["master_student_snapshot.csv"]}
        role_by_user = {row["user_id"]: row for row in data["users_roles.csv"]}
        admin_id = next(
            id_to_app_id[row["user_id"]]
            for row in data["users_roles.csv"]
            if row["role"].lower() == "admin"
        )
        module_for_student: dict[str, str] = {}
        for row in data["student_module_enrolments.csv"]:
            module_for_student.setdefault(row["student_id"], row["module_id"])
        wellness_source_referrals = {
            row["referral_id"] for row in data["referrals.csv"]
            if "wellbeing" in row["referral_category"].lower() or "wellness" in row["referral_category"].lower()
        }
        booking_referral_ids = {row["referral_id"] for row in data["wellness_bookings.csv"]}
        referral_rows = {
            row["referral_id"]: row for row in data["referrals.csv"]
            if row["referral_id"] in wellness_source_referrals | booking_referral_ids
        }
        app_referrals: dict[str, WellnessReferral] = {}
        for row in referral_rows.values():
            source_status = row["status"].strip().lower()
            active = row["referral_id"] in wellness_source_referrals and source_status not in ("resolved", "closed")
            app_referrals[row["referral_id"]] = WellnessReferral(
                id=row["referral_id"],
                student_id=row["student_id"],
                created_by=admin_id,
                assigned_to=id_to_app_id.get(row["assigned_advisor_id"]),
                status="active" if active else "closed",
                student_message=(
                    "Your university recommends speaking with a Student Wellness professional. "
                    "You can book a confidential appointment through your recommendations."
                    if active else "Your support recommendation has been recorded."
                ),
                created_at=datetime.combine(_date(row["referral_date"], "referrals.referral_date"), time.min),
            )
        _insert_batches(db, app_referrals.values())

        slots_by_id: dict[str, WellnessAppointmentSlot] = {}
        for row in data["wellness_slots.csv"]:
            start = _datetime(row["slot_start"], "wellness_slots.slot_start")
            end = _datetime(row["slot_end"], "wellness_slots.slot_end")
            slots_by_id[row["slot_id"]] = WellnessAppointmentSlot(
                id=row["slot_id"],
                starts_at=start,
                duration_minutes=max(15, int((end - start).total_seconds() / 60)),
                location=f"{row['service_type']} · {row['staff_name']}",
                created_by=admin_id,
                active=row["availability_status"].strip().lower() == "available",
            )
        _insert_batches(db, slots_by_id.values())
        status_map = {
            "confirmed": "confirmed",
            "requested": "requested",
            "completed": "completed",
            "cancelled": "cancelled",
            "no-show": "no_show",
        }
        _insert_batches(db, (
            WellnessAppointment(
                id=row["booking_id"],
                referral_id=row["referral_id"],
                slot_id=row["slot_id"],
                student_id=row["student_id"],
                status=status_map.get(row["booking_status"].strip().lower(), "requested"),
                booked_at=_datetime(row["booking_created_at"], "wellness_bookings.booking_created_at"),
            )
            for row in data["wellness_bookings.csv"]
            if row["referral_id"] in app_referrals
        ))

        db.flush()
        if state is None:
            state = ImportedDatasetState(dataset_id=DATASET_ID, content_sha256=digest)
            db.add(state)
        else:
            state.content_sha256 = digest
        db.commit()
        return id_to_app_id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _import_lms_database(
    data: dict[str, list[dict[str, str]]],
    digest: str,
    database_url: str,
    id_to_app_id: dict[str, str],
    replace: bool,
) -> dict[str, int | str]:
    engine, session_factory = build_lms_session_factory(database_url=database_url)
    LMSBase.metadata.create_all(bind=engine)
    db = session_factory()
    try:
        manifest = db.query(DatasetImport).filter(
            DatasetImport.source_name == DATASET_ID,
            DatasetImport.content_sha256 == digest,
        ).first()
        if manifest is not None:
            return {
                "status": "already_imported",
                "student_count": manifest.student_count,
                "module_count": db.query(Module).count(),
                "assessment_count": manifest.assessment_count,
            }
        if not replace and any(
            db.query(model).count()
            for model in (Student, Module, DatasetImport, DatasetSourceRow)
        ):
            raise ValueError("LMS database already contains a different dataset; use --replace to replace it")
        if replace:
            db.close()
            LMSBase.metadata.drop_all(bind=engine)
            LMSBase.metadata.create_all(bind=engine)
            db = session_factory()

        user_rows = {
            row["user_id"]: row for row in data["users_roles.csv"]
            if row["role"].strip().lower() in ROLE_MAP
        }
        app_user_ids = {
            row["user_id"]: id_to_app_id[row["user_id"]]
            for row in user_rows.values()
        }
        students_rows = data["students.csv"]
        programme_info: dict[str, tuple[str, str]] = {}
        for row in students_rows:
            programme_info.setdefault(row["programme"], (row["faculty"], "Undergraduate"))
        programme_id_by_name = {
            name: f"NSP{index:04d}"
            for index, name in enumerate(sorted(programme_info), start=1)
        }
        programmes = [
            Programme(
                programme_id=programme_id_by_name[name],
                programme_code=f"NSP{index:04d}",
                programme_name=name,
                faculty=programme_info[name][0],
                level=programme_info[name][1],
            )
            for index, name in enumerate(sorted(programme_info), start=1)
        ]
        db.add_all(programmes)
        lecturer_rows = [
            row for row in data["users_roles.csv"] if row["role"].strip().lower() == "lecturer"
        ]
        lecturer_by_id = {row["user_id"]: row for row in lecturer_rows}
        db.add_all(Lecturer(
            lecturer_id=row["user_id"],
            first_name=row["display_name"].split(" ", 1)[0],
            surname=row["display_name"].split(" ", 1)[1] if " " in row["display_name"] else row["display_name"],
            email=row["email"].lower(),
            department=next((item["faculty"] for item in data["modules.csv"] if item["lecturer_id"] == row["user_id"]), "Computing"),
        ) for row in lecturer_rows)
        db.flush()

        snapshot_rows = {row["student_id"]: row for row in data["master_student_snapshot.csv"]}
        students = [
            Student(
                student_id=row["student_id"],
                first_name=row["first_name"],
                surname=row["last_name"],
                institutional_email=row["email"].lower(),
                programme_id=programme_id_by_name[row["programme"]],
                year_of_study=_integer(row["year_of_study"], "students.year_of_study", 1),
                semester=1,
                behaviour_group=f"imported_{_slug(snapshot_rows[row['student_id']]['risk_band']).lower()}",
                enrolment_status=_slug(row["enrolment_status"]),
            )
            for row in students_rows
        ]
        db.add_all(students)
        db.add_all(StudentMapping(
            app_user_email=user_rows[row["student_id"]]["email"].lower(),
            student_id=row["student_id"],
        ) for row in students_rows)
        db.add_all(StaffMapping(
            app_user_email=row["email"].lower(),
            lecturer_id=row["user_id"],
        ) for row in lecturer_rows)
        db.flush()

        module_rows = data["modules.csv"]
        default_programme_id = next(iter(programme_id_by_name.values()))
        programme_by_module: dict[str, str] = {}
        module_programme = {}
        for row in data["student_module_enrolments.csv"]:
            module_programme.setdefault(row["module_id"], row["student_id"])
        programme_by_student = {row["student_id"]: programme_id_by_name[row["programme"]] for row in students_rows}
        for row in module_rows:
            programme_by_module[row["module_id"]] = programme_by_student.get(
                module_programme.get(row["module_id"], ""), default_programme_id
            )
        db.add_all(Module(
            module_id=row["module_id"],
            programme_id=programme_by_module[row["module_id"]],
            module_code=row["module_id"],
            module_name=row["module_name"],
            credits=20,
            semester=1,
            lecturer_id=row["lecturer_id"],
        ) for row in module_rows)
        db.flush()

        _insert_batches(db, (
            ModuleEnrolment(
                enrolment_id=f"ENR-{row['student_id']}-{row['module_id']}",
                student_id=row["student_id"],
                module_id=row["module_id"],
                status=_slug(row["enrolment_status"]),
                enrolled_at=_datetime(row["enrolled_on"], "student_module_enrolments.enrolled_on"),
            )
            for row in data["student_module_enrolments.csv"]
        ))

        assessment_rows = data["assessments.csv"]
        _insert_batches(db, (
            Assessment(
                assessment_id=row["assessment_id"],
                module_id=row["module_id"],
                title=row["assessment_title"],
                assessment_type=_slug(row["assessment_type"]),
                weight=100,
                maximum_mark=_number(row["max_score"], "assessments.max_score", 0.01),
                due_date=_date(row["assessment_date"], "assessments.assessment_date"),
            )
            for row in assessment_rows
        ))
        _insert_batches(db, (
            AssessmentResult(
                result_id=f"RES-{row['assessment_id']}",
                student_id=row["student_id"],
                assessment_id=row["assessment_id"],
                mark=_number(row["score_percent"], "assessments.score_percent", 0, 100),
                percentage=_number(row["score_percent"], "assessments.score_percent", 0, 100),
                submission_date=_date(row["assessment_date"], "assessments.assessment_date"),
                status=_slug(row["submission_status"]),
            )
            for row in assessment_rows
        ))
        _insert_batches(db, (
            Submission(
                submission_id=f"SUB-{row['assessment_id']}",
                student_id=row["student_id"],
                assessment_id=row["assessment_id"],
                submitted_at=(
                    datetime.combine(_date(row["assessment_date"], "assessments.assessment_date"), time.min)
                    if row["submission_status"].strip().lower() in ("submitted", "late") else None
                ),
                status=_slug(row["submission_status"]),
            )
            for row in assessment_rows
        ))

        session_ids: dict[tuple[str, date], str] = {}
        attendance_rows = data["attendance_records.csv"]
        for row in attendance_rows:
            key = (row["module_id"], _date(row["class_date"], "attendance_records.class_date"))
            session_ids.setdefault(key, f"CLS-{key[0]}-{key[1].strftime('%Y%m%d')}")
        _insert_batches(db, (
            AttendanceSession(
                session_id=session_id,
                module_id=module_id,
                session_date=class_date,
                session_type="CLASS",
            )
            for (module_id, class_date), session_id in session_ids.items()
        ))
        _insert_batches(db, (
            AttendanceRecord(
                attendance_id=row["attendance_id"],
                student_id=row["student_id"],
                module_id=row["module_id"],
                session_id=session_ids[(row["module_id"], _date(row["class_date"], "attendance_records.class_date"))],
                session_date=_date(row["class_date"], "attendance_records.class_date"),
                status="EXCUSED" if row["attendance_status"].strip().lower() == "approved leave" else _slug(row["attendance_status"]),
            )
            for row in attendance_rows
        ))
        grouped_attendance: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in attendance_rows:
            grouped_attendance[(row["student_id"], row["class_date"][:7])].append(row["attendance_status"].strip().lower())
        _insert_batches(db, (
            MonthlyAttendanceSummary(
                summary_id=f"SUM-{student_id}-{month.replace('-', '')}",
                student_id=student_id,
                month=month,
                scheduled_sessions=len(statuses),
                attended_sessions=sum(status in ("present", "late") for status in statuses),
                approved_leave_sessions=sum(status == "approved leave" for status in statuses),
                unexcused_absences=sum(status == "absent" for status in statuses),
                attendance_percentage=(
                    sum(status in ("present", "late") for status in statuses)
                    / max(1, sum(status != "approved leave" for status in statuses)) * 100
                ),
                source=DATASET_ID,
            )
            for (student_id, month), statuses in grouped_attendance.items()
        ))
        leave_rows = []
        for (student_id, month), statuses in grouped_attendance.items():
            leave_count = sum(status == "approved leave" for status in statuses)
            if leave_count:
                leave_rows.append(ApprovedLeaveRecord(
                    leave_id=f"LV-{student_id}-{month.replace('-', '')}",
                    student_id=student_id,
                    month=month,
                    sessions=leave_count,
                    reason=None,
                    approval_status="APPROVED",
                    source=DATASET_ID,
                ))
        _insert_batches(db, leave_rows)

        login_rows = data["login_activity.csv"]
        _insert_batches(db, (
            LMSActivity(
                activity_id=row["login_event_id"],
                student_id=row["student_id"],
                timestamp=_datetime(row["login_at"], "login_activity.login_at"),
                activity_type="LOGIN",
                module_id=None,
                session_duration=_integer(row["session_minutes"], "login_activity.session_minutes"),
            )
            for row in login_rows
        ))

        advisor_assignments = {
            row["student_id"]: row["advisor_id"]
            for row in data["advisor_assignments.csv"]
        }
        risk_by_student = {
            row["student_id"]: row
            for row in sorted(data["risk_assessments.csv"], key=lambda item: item["assessment_date"])
        }
        referral_rows = data["referrals.csv"]
        referrals: dict[str, Referral] = {}
        module_by_student: dict[str, str] = {}
        for row in data["student_module_enrolments.csv"]:
            module_by_student.setdefault(row["student_id"], row["module_id"])
        default_lecturer = module_rows[0]["lecturer_id"]
        for row in referral_rows:
            risk = risk_by_student.get(row["student_id"])
            risk_band = risk["risk_band"] if risk else "Unknown"
            score = float(risk["risk_score_0_100"]) if risk else 0.0
            status_map = {
                "new": "REFERRED",
                "assigned": "ASSIGNED",
                "awaiting student response": "AWAITING_STUDENT",
                "contact attempted": "CONTACT_ATTEMPTED",
                "meeting scheduled": "MEETING_SCHEDULED",
                "in progress": "UNDER_REVIEW",
                "resolved": "RESOLVED",
            }
            referrals[row["referral_id"]] = Referral(
                referral_id=row["referral_id"],
                student_id=row["student_id"],
                lecturer_id=default_lecturer,
                advisor_user_id=app_user_ids.get(row["assigned_advisor_id"]),
                module_id=module_by_student.get(row["student_id"]),
                risk_level=_slug(risk_band),
                risk_score=score,
                reason=row["reason_summary"],
                lecturer_notes=row["referral_category"],
                urgency="PRIORITY" if row["priority"].strip().lower() == "priority" else "STANDARD",
                status=status_map.get(row["status"].strip().lower(), _slug(row["status"])),
                created_at=_datetime(f"{row['referral_date']}T00:00:00", "referrals.referral_date"),
                updated_at=_datetime(f"{row['referral_date']}T00:00:00", "referrals.referral_date"),
            )
        _insert_batches(db, referrals.values())
        _insert_batches(db, (
            Intervention(
                intervention_id=row["intervention_id"],
                referral_id=row["referral_id"],
                student_id=row["student_id"],
                advisor_user_id=app_user_ids[row["advisor_id"]],
                strategy=row["intervention_type"],
                reason=row["action_plan"],
                advisor_notes=None,
                date_started=_datetime(f"{row['created_date']}T00:00:00", "interventions.created_date"),
                review_date=_date(row["review_date"], "interventions.review_date"),
                follow_up_date=None,
                outcome=row["outcome_summary"],
                status=_slug(row["status"]),
            )
            for row in data["interventions.csv"]
        ))

        for filename in sorted(PACK_FILES):
            rows = data[filename]
            source_batch = []
            workbook_batch = []
            for index, row in enumerate(rows, start=2):
                row_id = _source_identifier(filename, row, index)
                payload = _source_payload(filename, row)
                source_batch.append(DatasetSourceRow(
                    source_row_id=f"complete-pack:{filename}:{row_id}",
                    source_name=filename,
                    row_number=index,
                    payload=payload,
                ))
                workbook_batch.append(WorkbookIntelligence(
                    record_id=f"PACK-{Path(filename).stem.upper()}-{index:07d}",
                    sheet_name=Path(filename).stem,
                    row_number=index,
                    payload=payload,
                ))
                if len(source_batch) >= 2000:
                    _insert_batches(db, source_batch)
                    _insert_batches(db, workbook_batch)
                    source_batch.clear()
                    workbook_batch.clear()
            _insert_batches(db, source_batch)
            _insert_batches(db, workbook_batch)
        db.add(DatasetImport(
            import_id=f"PACK-{digest[:16]}",
            source_name=DATASET_ID,
            content_sha256=digest,
            student_count=len(students_rows),
            attendance_count=len(attendance_rows),
            assessment_count=len(assessment_rows),
            leave_count=len(leave_rows),
        ))
        db.commit()
        return {
            "status": "imported",
            "student_count": len(students_rows),
            "module_count": len(module_rows),
            "assessment_count": len(assessment_rows),
            "attendance_count": len(attendance_rows),
            "topic_feedback_count": len(data["lecturer_feedback.csv"]),
            "resource_count": len(data["learning_resources.csv"]),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


def import_complete_data_pack(
    bundle_path: str | Path = DEFAULT_BUNDLE,
    database_url: Optional[str] = None,
    replace: bool = False,
    *,
    app_database_engine=app_engine,
    app_session_factory: sessionmaker = SessionLocal,
) -> dict[str, int | str]:
    source = Path(bundle_path).expanduser().resolve(strict=True)
    if not zipfile.is_zipfile(source):
        raise ValueError("Dataset bundle is not a valid ZIP file")
    data, digest = _read_pack(source)
    target_url = database_url or CONFIGURED_LMS_DATABASE_URL or get_lms_database_url()
    lms_engine, lms_factory = build_lms_session_factory(database_url=target_url)
    LMSBase.metadata.create_all(bind=lms_engine)
    Base.metadata.create_all(bind=app_database_engine)
    _ensure_resource_columns(app_database_engine)
    lms_db = lms_factory()
    try:
        manifest = lms_db.query(DatasetImport).filter(
            DatasetImport.source_name == DATASET_ID,
            DatasetImport.content_sha256 == digest,
        ).first()
        app_db = app_session_factory()
        try:
            app_state = app_db.query(ImportedDatasetState).filter(
                ImportedDatasetState.dataset_id == DATASET_ID,
                ImportedDatasetState.content_sha256 == digest,
            ).first()
            if manifest is not None and app_state is not None:
                return {
                    "status": "already_imported",
                    "student_count": manifest.student_count,
                    "module_count": lms_db.query(Module).count(),
                    "assessment_count": manifest.assessment_count,
                }
        finally:
            app_db.close()
    finally:
        lms_db.close()
        lms_engine.dispose()

    app_mapping = _reset_app_database(data, digest, app_database_engine, app_session_factory, replace)
    return _import_lms_database(data, digest, target_url, app_mapping, replace)


def ensure_complete_data_pack_seeded(
    bundle_path: str | Path = DEFAULT_BUNDLE,
    database_url: Optional[str] = None,
    *,
    replace_legacy_dataset: bool = False,
) -> Optional[dict[str, int | str]]:
    source = Path(bundle_path).expanduser().resolve(strict=True)
    _, digest = _read_pack(source)
    target_url = database_url or CONFIGURED_LMS_DATABASE_URL or get_lms_database_url()
    lms_engine, lms_factory = build_lms_session_factory(database_url=target_url)
    LMSBase.metadata.create_all(bind=lms_engine)
    lms_db = lms_factory()
    try:
        existing = lms_db.query(DatasetImport).filter(
            DatasetImport.source_name == DATASET_ID,
            DatasetImport.content_sha256 == digest,
        ).first()
        if existing is not None:
            app_db = SessionLocal()
            try:
                state = app_db.query(ImportedDatasetState).filter(
                    ImportedDatasetState.dataset_id == DATASET_ID,
                    ImportedDatasetState.content_sha256 == digest,
                ).first()
                if state is not None:
                    return None
            finally:
                app_db.close()
        has_dataset = bool(
            lms_db.query(Student).count()
            or lms_db.query(Module).count()
            or lms_db.query(DatasetImport).count()
        )
    finally:
        lms_db.close()
        lms_engine.dispose()

    if has_dataset and not replace_legacy_dataset:
        return None
    return import_complete_data_pack(
        source,
        target_url,
        replace=has_dataset or replace_legacy_dataset,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the complete NeuroSync synthetic demo CSV data pack.")
    parser.add_argument("bundle", nargs="?", default=str(DEFAULT_BUNDLE), help="Path to the CSV data-pack ZIP")
    parser.add_argument(
        "--database-url",
        default=CONFIGURED_LMS_DATABASE_URL or get_lms_database_url(),
        help="Target LMS database URL",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the existing demo dataset in both the LMS and app databases",
    )
    args = parser.parse_args()
    print(import_complete_data_pack(args.bundle, args.database_url, replace=args.replace))


if __name__ == "__main__":
    main()
