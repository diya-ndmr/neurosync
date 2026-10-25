"""Import the extended CSV bundle as a separate, namespaced student cohort."""

import argparse
import csv
import io
import math
import os
import uuid
import zipfile
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import Base, SessionLocal, engine
from app.models import (
    ExtendedAssessmentFeedback,
    ExtendedQuizQuestionResult,
    MoodCheckin,
    Recommendation,
    RiskPrediction,
    StudentProfile,
    StudySession,
    User,
)
from app.models.risk_prediction import RiskLevel
from app.models.user import UserRole
from app.services.authentication_service import hash_password

DEFAULT_BUNDLE = Path(__file__).resolve().parents[1] / "datasets" / "NeuroSync_Extended_Data.zip"
FILES = {
    "assessment_feedback.csv": {"student_id", "assessment_id", "feedback_text"},
    "quiz_question_results.csv": {"student_id", "assessment_id", "question_id", "is_correct"},
    "risk_predictions.csv": {"student_id", "prediction_date", "risk_score", "risk_level", "primary_risk_factor"},
    "mood_and_study_sessions.csv": {
        "student_id",
        "date",
        "mood_score",
        "stress_score",
        "session_start_time",
        "duration_minutes",
    },
    "student_recommendations.csv": {
        "student_id",
        "recommendation_date",
        "recommendation_type",
        "recommendation_text",
    },
    "students_extended.csv": {"student_id", "first_name", "last_name", "email", "phone_number"},
}
NAMESPACE = uuid.UUID("f9fe45f8-1899-47d7-9061-7feb99e3df5a")


def _stable_id(kind: str, *parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, ":".join((kind, *parts))))


def _read_bundle(bundle: Path) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(bundle) as archive:
        members: dict[str, str] = {}
        for name in archive.namelist():
            filename = Path(name.replace("\\", "/")).name
            if filename not in FILES:
                continue
            if filename in members:
                raise ValueError(f"Dataset ZIP contains duplicate {filename}")
            members[filename] = name
        missing = FILES.keys() - members.keys()
        if missing:
            raise ValueError(f"Dataset ZIP is missing CSV files: {', '.join(sorted(missing))}")

        result: dict[str, list[dict[str, str]]] = {}
        for filename, member in members.items():
            with archive.open(member) as source:
                reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ValueError(f"{filename} has missing or duplicate CSV headers")
                missing_columns = FILES[filename] - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(f"{filename} is missing columns: {', '.join(sorted(missing_columns))}")
                rows = list(reader)
            if not rows or any(None in row for row in rows):
                raise ValueError(f"{filename} contains no rows or a row with extra values")
            result[filename] = rows
    _validate_rows(result)
    return result


def _required(row: dict[str, str], field: str, source: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"{source}.{field} is required")
    return value


def _parse_date(value: str, source: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{source} must be an ISO date") from error


def _parse_int(value: str, source: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{source} must be an integer") from error
    if not minimum <= parsed <= maximum:
        raise ValueError(f"{source} is outside the allowed range")
    return parsed


def _account_emails(roster: list[dict[str, str]]) -> dict[str, str]:
    counts = Counter(row["email"].strip().lower() for row in roster)
    result = {}
    for row in roster:
        source_id = row["student_id"].strip()
        email = row["email"].strip().lower()
        if counts[email] > 1:
            local, domain = email.rsplit("@", 1)
            email = f"{local}+ext-{source_id.lower()}@{domain}"
        result[source_id] = email
    return result


def _validate_rows(rows: dict[str, list[dict[str, str]]]) -> None:
    roster: dict[str, dict[str, str]] = {}
    for row in rows["students_extended.csv"]:
        student_id = _required(row, "student_id", "students_extended")
        email = _required(row, "email", "students_extended").lower()
        _required(row, "first_name", "students_extended")
        _required(row, "last_name", "students_extended")
        if student_id in roster:
            raise ValueError(f"students_extended.csv has duplicate student_id {student_id}")
        if email.count("@") != 1 or not all(email.split("@")):
            raise ValueError(f"students_extended.csv has an invalid email: {email}")
        roster[student_id] = row

    account_emails = _account_emails(list(roster.values()))
    if len(set(account_emails.values())) != len(account_emails):
        raise ValueError("students_extended.csv cannot be converted into unique login emails")

    for filename, file_rows in rows.items():
        for row in file_rows:
            student_id = _required(row, "student_id", filename.removesuffix(".csv"))
            if student_id not in roster:
                raise ValueError(f"{filename} references unknown student_id {student_id}")

    feedback_keys: set[tuple[str, str]] = set()
    for row in rows["assessment_feedback.csv"]:
        key = (_required(row, "student_id", "assessment_feedback"), _required(row, "assessment_id", "assessment_feedback"))
        _required(row, "feedback_text", "assessment_feedback")
        if key in feedback_keys:
            raise ValueError(f"assessment_feedback.csv has duplicate student/assessment row {key}")
        feedback_keys.add(key)

    question_keys: set[tuple[str, str, str]] = set()
    for row in rows["quiz_question_results.csv"]:
        key = (
            _required(row, "student_id", "quiz_question_results"),
            _required(row, "assessment_id", "quiz_question_results"),
            _required(row, "question_id", "quiz_question_results"),
        )
        answer = _required(row, "is_correct", "quiz_question_results").lower()
        if answer not in {"true", "false"}:
            raise ValueError("quiz_question_results.is_correct must be true or false")
        if key in question_keys:
            raise ValueError(f"quiz_question_results.csv has duplicate question row {key}")
        question_keys.add(key)

    for row in rows["risk_predictions.csv"]:
        _parse_date(_required(row, "prediction_date", "risk_predictions"), "risk_predictions.prediction_date")
        try:
            score = float(_required(row, "risk_score", "risk_predictions"))
            RiskLevel(_required(row, "risk_level", "risk_predictions").upper())
        except (ValueError, TypeError) as error:
            raise ValueError("risk_predictions contains an invalid score or risk level") from error
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("risk_predictions.risk_score must be between 0 and 1")
        _required(row, "primary_risk_factor", "risk_predictions")

    for row in rows["mood_and_study_sessions.csv"]:
        _parse_date(_required(row, "date", "mood_and_study_sessions"), "mood_and_study_sessions.date")
        try:
            time.fromisoformat(_required(row, "session_start_time", "mood_and_study_sessions"))
        except ValueError as error:
            raise ValueError("mood_and_study_sessions.session_start_time must be an ISO time") from error
        _parse_int(_required(row, "mood_score", "mood_and_study_sessions"), "mood_score", 1, 10)
        _parse_int(_required(row, "stress_score", "mood_and_study_sessions"), "stress_score", 1, 10)
        _parse_int(_required(row, "duration_minutes", "mood_and_study_sessions"), "duration_minutes", 1, 1440)

    for row in rows["student_recommendations.csv"]:
        _parse_date(_required(row, "recommendation_date", "student_recommendations"), "recommendation_date")
        _required(row, "recommendation_type", "student_recommendations")
        _required(row, "recommendation_text", "student_recommendations")


def import_extended_data_pack(db: Session, bundle: Path, initial_password: str) -> dict[str, int]:
    if not initial_password:
        raise ValueError("An initial password is required for the extended cohort accounts")
    rows = _read_bundle(bundle)
    roster = rows["students_extended.csv"]
    account_emails = _account_emails(roster)

    normalized_emails = list(account_emails.values())
    existing_by_email = {
        user.email.lower(): user
        for user in db.query(User).filter(func.lower(User.email).in_(normalized_emails)).all()
    }
    email_collisions = []
    for row in roster:
        source_id = row["student_id"].strip()
        email = account_emails[source_id]
        existing_user = existing_by_email.get(email)
        expected_user_id = f"EXT-USER-{source_id}"
        if existing_user is not None and existing_user.id != expected_user_id:
            email_collisions.append(email)
    if email_collisions:
        raise ValueError(f"Extended cohort email already exists in NeuroSync: {', '.join(sorted(email_collisions))}")

    try:
        for row in roster:
            source_id = row["student_id"].strip()
            student_id = f"EXT-{source_id}"
            user_id = f"EXT-USER-{source_id}"
            email = account_emails[source_id]
            existing = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
            if existing and existing.user_id != user_id:
                raise ValueError(f"Student ID collision for {student_id}")

            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                user = User(
                    id=user_id,
                    email=email,
                    password_hash=hash_password(initial_password),
                    name=f"{row['first_name'].strip()} {row['last_name'].strip()}",
                    role=UserRole.student,
                )
                db.add(user)
            elif user.email.lower() != email:
                raise ValueError(f"User email changed for {student_id}; refusing to overwrite the account")

            if existing is None:
                db.add(
                    StudentProfile(
                        id=student_id,
                        user_id=user_id,
                        student_number=student_id,
                        first_name=row["first_name"].strip(),
                        surname=row["last_name"].strip(),
                        programme="Not provided",
                        year_level=0,
                    )
                )
        db.flush()

        imported: dict[str, int] = {"students": len(roster)}

        feedback_rows = rows["assessment_feedback.csv"]
        for row in feedback_rows:
            source_id = row["student_id"].strip()
            assessment_id = row["assessment_id"].strip()
            db.merge(
                ExtendedAssessmentFeedback(
                    id=_stable_id("feedback", source_id, assessment_id),
                    student_id=f"EXT-{source_id}",
                    external_assessment_id=assessment_id,
                    feedback_text=row["feedback_text"].strip(),
                )
            )
        imported["assessment_feedback"] = len(feedback_rows)

        question_rows = rows["quiz_question_results.csv"]
        for row in question_rows:
            source_id = row["student_id"].strip()
            assessment_id = row["assessment_id"].strip()
            question_id = row["question_id"].strip()
            db.merge(
                ExtendedQuizQuestionResult(
                    id=_stable_id("question", source_id, assessment_id, question_id),
                    student_id=f"EXT-{source_id}",
                    external_assessment_id=assessment_id,
                    question_id=question_id,
                    is_correct=row["is_correct"].strip().lower() == "true",
                )
            )
        imported["quiz_question_results"] = len(question_rows)

        risk_rows = rows["risk_predictions.csv"]
        for row in risk_rows:
            source_id = row["student_id"].strip()
            prediction_date = _parse_date(row["prediction_date"], "risk_predictions.prediction_date")
            score = float(row["risk_score"]) * 100
            factor = row["primary_risk_factor"].strip()
            created_at = datetime.combine(prediction_date, time.min)
            db.merge(
                RiskPrediction(
                    id=_stable_id("risk", source_id, prediction_date.isoformat()),
                    student_id=f"EXT-{source_id}",
                    risk_score=round(score, 1),
                    risk_level=RiskLevel(row["risk_level"].strip().upper()),
                    explanation=f"Primary recorded risk factor: {factor}. Imported screening signal; review the underlying records with the student.",
                    model_version="extended_data_import_v1",
                    created_at=created_at,
                )
            )
        imported["risk_predictions"] = len(risk_rows)

        activity_rows = rows["mood_and_study_sessions.csv"]
        for index, row in enumerate(activity_rows, start=1):
            source_id = row["student_id"].strip()
            activity_date = _parse_date(row["date"], "mood_and_study_sessions.date")
            start_time = time.fromisoformat(row["session_start_time"].strip())
            date_key = f"{activity_date.isoformat()}T{start_time.isoformat()}:{index}"
            created_at = datetime.combine(activity_date, start_time)
            db.merge(
                MoodCheckin(
                    id=_stable_id("mood", source_id, date_key),
                    student_id=f"EXT-{source_id}",
                    mood_score=int(row["mood_score"]),
                    stress_level=int(row["stress_score"]),
                    notes=None,
                    created_at=datetime.combine(activity_date, time.min),
                )
            )
            db.merge(
                StudySession(
                    id=_stable_id("study", source_id, date_key),
                    student_id=f"EXT-{source_id}",
                    subject="Not provided",
                    duration_minutes=int(row["duration_minutes"]),
                    activity_type="Not provided",
                    created_at=created_at,
                )
            )
        imported["mood_checkins"] = len(activity_rows)
        imported["study_sessions"] = len(activity_rows)

        recommendation_rows = rows["student_recommendations.csv"]
        category_map = {
            "academic": "academic",
            "attendance": "attendance",
            "wellness": "wellbeing",
            "wellbeing": "wellbeing",
            "study": "study",
            "administrative": "administrative",
        }
        for row in recommendation_rows:
            source_id = row["student_id"].strip()
            category = row["recommendation_type"].strip().lower()
            if category not in category_map:
                raise ValueError(f"Unsupported recommendation type: {row['recommendation_type']}")
            recommendation_date = _parse_date(row["recommendation_date"], "recommendation_date")
            message = row["recommendation_text"].strip()
            db.merge(
                Recommendation(
                    id=_stable_id("recommendation", source_id, recommendation_date.isoformat(), category, message),
                    student_id=f"EXT-{source_id}",
                    category=category_map[category],
                    message=message,
                    priority="medium",
                    status="new",
                    created_at=datetime.combine(recommendation_date, time.min),
                )
            )
        imported["recommendations"] = len(recommendation_rows)

        db.commit()
        return imported
    except Exception:
        db.rollback()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the extended dataset into an isolated student cohort.")
    parser.add_argument("bundle", nargs="?", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args()
    initial_password = os.environ.get("NEUROSYNC_EXTENDED_INITIAL_PASSWORD", "")
    if not initial_password:
        parser.error("Set NEUROSYNC_EXTENDED_INITIAL_PASSWORD to a demo-only password before importing.")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        summary = import_extended_data_pack(db, args.bundle, initial_password)
    finally:
        db.close()
    print("Imported isolated extended cohort:")
    for name, count in summary.items():
        print(f"  {name}: {count}")
    print("Student sign-in format: email from students_extended.csv; initial password is the configured demo password.")


if __name__ == "__main__":
    main()
