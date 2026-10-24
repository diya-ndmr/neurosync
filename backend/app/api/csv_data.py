import csv
import io
import itertools
import logging
import math
from datetime import date
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.database.connection import get_db
from app.middleware.security import require_role
from app.models.assessment import Assessment
from app.models.attendance import Attendance
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.services.audit_service import record_audit_event
from lms.database import LMSSessionLocal
from lms.models import Intervention, Referral, StudentMeeting, WorkbookIntelligence

router = APIRouter(prefix="/api/admin/csv", tags=["CSV data"])
logger = logging.getLogger(__name__)

ImportDataset = Literal["students", "modules", "attendance", "assessments"]
ExportDataset = Literal[
    "students", "modules", "attendance", "assessments",
    "referrals", "interventions", "meetings", "workbook-intelligence",
]
ImportMode = Literal["create", "update", "upsert"]
MAX_CSV_FILE_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 10_000
PREVIEW_ROW_LIMIT = 100
NATURAL_KEY_BATCH_SIZE = 300

IMPORT_COLUMNS: dict[str, tuple[str, ...]] = {
    "students": ("student_number", "email", "first_name", "surname", "programme", "year_level"),
    "modules": ("module_code", "module_name", "faculty"),
    "attendance": ("student_number", "module_code", "attendance_percentage", "date"),
    "assessments": ("student_number", "module_code", "assessment_type", "mark", "assessment_date"),
}
EMAIL_TYPE = TypeAdapter(EmailStr)

EXPORT_COLUMNS: dict[str, tuple[str, ...]] = {
    "students": ("student_number", "email", "first_name", "surname", "programme", "year_level"),
    "modules": ("module_code", "module_name", "faculty"),
    "attendance": ("student_number", "module_code", "attendance_percentage", "date"),
    "assessments": ("student_number", "module_code", "assessment_type", "mark", "assessment_date"),
    "referrals": (
        "referral_id", "student_id", "lecturer_id", "advisor_user_id", "module_id", "risk_assessment_id",
        "risk_level", "risk_score", "reason", "lecturer_notes", "urgency", "status", "created_at", "updated_at",
    ),
    "interventions": (
        "intervention_id", "referral_id", "student_id", "advisor_user_id", "strategy", "reason",
        "advisor_notes", "date_started", "review_date", "follow_up_date", "outcome", "status",
        "created_at", "updated_at",
    ),
    "meetings": (
        "meeting_id", "referral_id", "student_id", "advisor_user_id", "meeting_at", "purpose",
        "status", "advisor_notes", "created_at",
    ),
    "workbook-intelligence": ("record_id", "sheet_name", "row_number", "payload"),
}


def _error(row: int, field: Optional[str], code: str, message: str) -> dict[str, Any]:
    return {"row": row, "field": field, "code": code, "message": message}


async def _read_upload(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a .csv file.")
    content = await file.read(MAX_CSV_FILE_BYTES + 1)
    if len(content) > MAX_CSV_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV exceeds the 5 MiB limit.")
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV file is empty.")
    return content


def _parse_csv(content: bytes, dataset: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [_error(1, None, "encoding", "File must use UTF-8 encoding.")], 0

    stream = io.StringIO(text, newline="")
    try:
        reader = csv.DictReader(stream, restkey="__extra_values__", restval=None, strict=True)
        if reader.fieldnames is None:
            return [], [_error(1, None, "missing_header", "CSV must include a header row.")], 0

        headers = [header.strip() if header else "" for header in reader.fieldnames]
        expected = IMPORT_COLUMNS[dataset]
        errors: list[dict[str, Any]] = []
        if any(not header for header in headers):
            errors.append(_error(1, None, "empty_header", "Column names cannot be blank."))
        if len(set(headers)) != len(headers):
            errors.append(_error(1, None, "duplicate_header", "Column names must be unique."))
        missing = [column for column in expected if column not in headers]
        unexpected = [column for column in headers if column and column not in expected]
        for column in missing:
            errors.append(_error(1, column, "missing_header", f"Required column '{column}' is missing."))
        for column in unexpected:
            errors.append(_error(1, column, "unexpected_header", f"Column '{column}' is not supported."))
        if errors:
            return [], errors, 0
        reader.fieldnames = headers

        rows: list[dict[str, Any]] = []
        total_rows = 0
        previous_line = reader.line_num
        for raw in reader:
            line_number = previous_line + 1
            previous_line = reader.line_num
            total_rows += 1
            if total_rows > MAX_CSV_ROWS:
                return [], [_error(line_number, None, "row_limit", f"CSV exceeds the {MAX_CSV_ROWS} row limit.")], total_rows
            if raw.get("__extra_values__") is not None:
                errors.append(_error(line_number, None, "extra_values", "Row contains more values than the header."))
                continue
            rows.append({"_row": line_number, **{key: raw.get(key) for key in expected}})
        if not rows and not errors:
            errors.append(_error(2, None, "empty_file", "CSV contains a header but no data rows."))
        return rows, errors, total_rows
    except csv.Error:
        return [], [_error(reader.line_num + 1, None, "malformed_csv", "CSV contains malformed quoting or rows.")], 0


def _parse_value(row: int, field: str, value: Any, errors: list[dict[str, Any]]) -> Optional[str]:
    if value is None or not str(value).strip():
        errors.append(_error(row, field, "missing_value", f"'{field}' is required."))
        return None
    result = str(value).strip()
    if result.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        errors.append(_error(row, field, "unsafe_formula", "Formula-like cell values are not accepted."))
        return None
    return result


def _validate_rows(
    raw_rows: list[dict[str, Any]],
    initial_errors: list[dict[str, Any]],
    dataset: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors = list(initial_errors)
    rows: list[dict[str, Any]] = []
    seen_keys: dict[str, set[str]] = {}
    for raw in raw_rows:
        line = raw["_row"]
        start_error_count = len(errors)
        parsed = {"_row": line}
        for field in IMPORT_COLUMNS[dataset]:
            parsed[field] = _parse_value(line, field, raw.get(field), errors)

        if len(errors) != start_error_count:
            continue

        if dataset == "students":
            parsed["student_number"] = parsed["student_number"].upper()
            parsed["email"] = parsed["email"].lower()
            try:
                parsed["email"] = str(EMAIL_TYPE.validate_python(parsed["email"]))
            except ValidationError:
                errors.append(_error(line, "email", "invalid_email", "Enter a valid email address."))
            try:
                parsed["year_level"] = int(parsed["year_level"])
                if not 1 <= parsed["year_level"] <= 10:
                    raise ValueError
            except ValueError:
                errors.append(_error(line, "year_level", "invalid_number", "Year level must be an integer from 1 to 10."))
            for field, limit in (("student_number", 64), ("email", 320), ("first_name", 120), ("surname", 120), ("programme", 120)):
                if len(parsed[field]) > limit:
                    errors.append(_error(line, field, "value_too_long", f"'{field}' cannot exceed {limit} characters."))
            keys = ("student_number", "email")
        elif dataset == "modules":
            parsed["module_code"] = parsed["module_code"].upper()
            for field, limit in (("module_code", 32), ("module_name", 200), ("faculty", 120)):
                if len(parsed[field]) > limit:
                    errors.append(_error(line, field, "value_too_long", f"'{field}' cannot exceed {limit} characters."))
            keys = ("module_code",)
        elif dataset == "attendance":
            parsed["student_number"] = parsed["student_number"].upper()
            parsed["module_code"] = parsed["module_code"].upper()
            try:
                parsed["attendance_percentage"] = float(parsed["attendance_percentage"])
                if not math.isfinite(parsed["attendance_percentage"]) or not 0 <= parsed["attendance_percentage"] <= 100:
                    raise ValueError
            except ValueError:
                errors.append(_error(line, "attendance_percentage", "invalid_number", "Attendance must be a finite number from 0 to 100."))
            try:
                parsed["date"] = date.fromisoformat(parsed["date"])
            except ValueError:
                errors.append(_error(line, "date", "invalid_date", "Date must use ISO format YYYY-MM-DD."))
            keys = ("student_number", "module_code", "date")
        else:
            parsed["student_number"] = parsed["student_number"].upper()
            parsed["module_code"] = parsed["module_code"].upper()
            try:
                parsed["mark"] = float(parsed["mark"])
                if not math.isfinite(parsed["mark"]) or not 0 <= parsed["mark"] <= 100:
                    raise ValueError
            except ValueError:
                errors.append(_error(line, "mark", "invalid_number", "Mark must be a finite number from 0 to 100."))
            try:
                parsed["assessment_date"] = date.fromisoformat(parsed["assessment_date"])
            except ValueError:
                errors.append(_error(line, "assessment_date", "invalid_date", "Date must use ISO format YYYY-MM-DD."))
            if len(parsed["assessment_type"]) > 64:
                errors.append(_error(line, "assessment_type", "value_too_long", "'assessment_type' cannot exceed 64 characters."))
            keys = ("student_number", "module_code", "assessment_type", "assessment_date")

        if any(error["row"] == line for error in errors):
            continue
        key = "\x1f".join(str(parsed[field]).casefold() for field in keys)
        seen = seen_keys.setdefault(dataset, set())
        if key in seen:
            errors.append(_error(line, None, "duplicate_row", "This row duplicates an identifier already present in the file."))
            continue
        seen.add(key)
        rows.append(parsed)
    return rows, errors


def _database_errors(
    db: Session,
    dataset: str,
    rows: list[dict[str, Any]],
    mode: ImportMode,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    student_numbers = {row["student_number"] for row in rows if "student_number" in row}
    module_codes = {row["module_code"] for row in rows if "module_code" in row}
    students: dict[str, StudentProfile] = {}
    modules: dict[str, Module] = {}

    if student_numbers:
        matched = (
            db.query(StudentProfile, User.email)
            .join(User, User.id == StudentProfile.user_id)
            .filter(func.upper(StudentProfile.student_number).in_(student_numbers))
            .all()
        )
        students = {student.student_number.upper(): student for student, _ in matched}
    if module_codes:
        modules = {
            module.module_code.upper(): module
            for module in db.query(Module).filter(func.upper(Module.module_code).in_(module_codes)).all()
        }

    if dataset == "students":
        emails = {row["email"] for row in rows}
        users = {
            user.email.lower(): user
            for user in db.query(User).filter(func.lower(User.email).in_(emails)).all()
        }
        student_emails_by_number = {
            student.student_number.upper(): email
            for student, email in matched
        } if student_numbers else {}
        profiles_by_user_id = {
            profile.user_id: profile
            for profile in db.query(StudentProfile).filter(
                StudentProfile.user_id.in_([user.id for user in users.values()])
            ).all()
        } if users else {}
        seen_emails: set[str] = set()
        for row in rows:
            line = row["_row"]
            email = row["email"]
            existing = students.get(row["student_number"])
            if email in seen_emails:
                errors.append(_error(line, "email", "duplicate_identifier", "Email is used more than once in this file."))
            seen_emails.add(email)
            user = users.get(email)
            if user is None:
                errors.append(_error(line, "email", "unknown_user", "Email must belong to an existing registered account."))
            elif user.role != UserRole.student:
                errors.append(_error(line, "email", "identifier_conflict", "Student profile must be linked to a student account."))
            if existing:
                owner_email = student_emails_by_number.get(row["student_number"], "")
                if mode == "create":
                    errors.append(_error(line, "student_number", "duplicate_identifier", "Student number already exists; choose update or upsert explicitly."))
                elif owner_email.lower() != email:
                    errors.append(_error(line, "email", "identifier_conflict", "Student number is already linked to a different user account."))
            elif mode == "update":
                errors.append(_error(line, "student_number", "not_found", "Update mode only accepts existing student numbers."))
            elif user and user.id in profiles_by_user_id:
                errors.append(_error(line, "email", "identifier_conflict", "User already has a different student profile."))
    elif dataset == "modules":
        for row in rows:
            existing = modules.get(row["module_code"])
            if existing and mode == "create":
                errors.append(_error(row["_row"], "module_code", "duplicate_identifier", "Module code already exists; choose update or upsert explicitly."))
            elif not existing and mode == "update":
                errors.append(_error(row["_row"], "module_code", "not_found", "Update mode only accepts existing module codes."))
    else:
        student_id_by_number = {number: student.id for number, student in students.items()}
        module_id_by_code = {code: module.id for code, module in modules.items()}
        keys: list[tuple[Any, ...]] = []
        key_rows: dict[tuple[Any, ...], int] = {}
        for row in rows:
            line = row["_row"]
            student_id = student_id_by_number.get(row["student_number"])
            module_id = module_id_by_code.get(row["module_code"])
            if student_id is None:
                errors.append(_error(line, "student_number", "unknown_student", "Student number does not exist."))
            if module_id is None:
                errors.append(_error(line, "module_code", "unknown_module", "Module code does not exist."))
            if student_id is None or module_id is None:
                continue
            if dataset == "attendance":
                row["_student_id"], row["_module_id"] = student_id, module_id
                key = (student_id, module_id, row["date"])
            else:
                row["_student_id"], row["_module_id"] = student_id, module_id
                key = (student_id, module_id, row["assessment_type"], row["assessment_date"])
            if key in key_rows:
                errors.append(_error(line, None, "duplicate_row", "This student, module, date, and record type already appears in the file."))
            key_rows[key] = line
            keys.append(key)

        existing_keys: set[tuple[Any, ...]] = set()
        model = Attendance if dataset == "attendance" else Assessment
        columns = (
            (Attendance.student_id, Attendance.module_id, Attendance.date)
            if dataset == "attendance"
            else (Assessment.student_id, Assessment.module_id, Assessment.assessment_type, Assessment.assessment_date)
        )
        unique_keys = list(set(keys))
        for index in range(0, len(unique_keys), NATURAL_KEY_BATCH_SIZE):
            batch = unique_keys[index:index + NATURAL_KEY_BATCH_SIZE]
            if batch:
                existing_keys.update(
                    tuple(record)
                    for record in db.query(*columns).filter(tuple_(*columns).in_(batch)).all()
                )
        for key in existing_keys:
            line = key_rows.get(key)
            if line is not None:
                errors.append(_error(line, None, "duplicate_record", "A matching record already exists; importing will not overwrite it."))

    return errors, {"students": students, "modules": modules, "users_by_email": locals().get("users", {})}


def _summary(
    total_rows: int,
    rows: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    preview: bool,
) -> dict[str, Any]:
    invalid_lines = {error["row"] for error in errors if error["row"] > 1}
    duplicate_lines = {error["row"] for error in errors if error["code"].startswith("duplicate")}
    candidate_lines = {row["_row"] for row in rows}
    valid_count = len(candidate_lines - invalid_lines)
    file_rejected = any(error["row"] == 1 or error["code"] == "row_limit" for error in errors)
    invalid_count = total_rows if file_rejected and total_rows else len(invalid_lines)
    if not total_rows and errors:
        invalid_count = 1
    return {
        "total_rows": total_rows,
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": len(duplicate_lines),
        "persisted_rows": 0,
        "preview": [
            {key: value.isoformat() if isinstance(value, date) else value for key, value in row.items() if not key.startswith("_")}
            for row in rows[:PREVIEW_ROW_LIMIT]
        ] if preview else [],
        "errors": errors[:500],
        "errors_truncated": len(errors) > 500,
    }


def _audit_import(
    db: Session,
    user: User,
    request: Request,
    dataset: str,
    outcome: str,
) -> None:
    record_audit_event(
        db,
        action=f"CSV_IMPORT_{dataset.upper()}",
        outcome=outcome,
        actor_reference=user.email.lower(),
        actor_id=user.id,
        request_id=getattr(request.state, "request_id", None),
        source_ip=request.client.host if request.client else None,
    )


async def _stage_upload(file: UploadFile, dataset: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    content = await _read_upload(file)
    raw_rows, errors, total_rows = _parse_csv(content, dataset)
    rows, errors = _validate_rows(raw_rows, errors, dataset)
    return rows, errors, total_rows


@router.get("/datasets")
def list_csv_datasets(current_user: User = Depends(require_role(UserRole.admin))):
    return {
        "import": {
            "students": {"columns": list(IMPORT_COLUMNS["students"]), "modes": ["create", "update", "upsert"]},
            "modules": {"columns": list(IMPORT_COLUMNS["modules"]), "modes": ["create", "update", "upsert"]},
            "attendance": {"columns": list(IMPORT_COLUMNS["attendance"]), "modes": ["create"]},
            "assessments": {"columns": list(IMPORT_COLUMNS["assessments"]), "modes": ["create"]},
        },
        "export": {dataset: list(columns) for dataset, columns in EXPORT_COLUMNS.items()},
        "rules": {
            "students": "Student numbers are case-insensitive identifiers. Student emails must already belong to a registered student account; imports never create login accounts. Create rejects existing numbers, update rejects new numbers, and upsert only updates a profile linked to the same email.",
            "modules": "Module codes are case-insensitive identifiers. Create rejects existing codes, update rejects new codes, and upsert creates or updates by module code.",
            "attendance": "Append-only. Each student, module, and date may be imported once; existing records are never overwritten.",
            "assessments": "Append-only. Each student, module, assessment type, and date may be imported once; existing records are never overwritten.",
        },
        "max_file_bytes": MAX_CSV_FILE_BYTES,
        "max_rows": MAX_CSV_ROWS,
    }


@router.post("/import/{dataset}/preview")
async def preview_csv_import(
    dataset: ImportDataset,
    file: UploadFile = File(...),
    mode: ImportMode = Query(default="create"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    if dataset not in ("students", "modules") and mode != "create":
        raise HTTPException(status_code=422, detail="Update and upsert modes are only supported for students and modules.")
    rows, errors, total_rows = await _stage_upload(file, dataset)
    if rows:
        database_errors, _ = _database_errors(db, dataset, rows, mode)
        errors.extend(database_errors)
    return _summary(total_rows, rows, errors, preview=True)


@router.post("/import/{dataset}")
async def import_csv(
    dataset: ImportDataset,
    request: Request,
    file: UploadFile = File(...),
    mode: ImportMode = Query(default="create"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    if dataset not in ("students", "modules") and mode != "create":
        raise HTTPException(status_code=422, detail="Update and upsert modes are only supported for students and modules.")
    rows, errors, total_rows = await _stage_upload(file, dataset)
    database_errors, lookup = _database_errors(db, dataset, rows, mode) if rows else ([], {})
    errors.extend(database_errors)
    summary = _summary(total_rows, rows, errors, preview=False)
    if errors or not rows:
        _audit_import(db, current_user, request, dataset, "REJECTED")
        db.commit()
        raise HTTPException(status_code=422, detail=summary)

    created = 0
    updated = 0
    try:
        for row in rows:
            if dataset == "students":
                existing = lookup["students"].get(row["student_number"])
                if existing:
                    existing.first_name = row["first_name"]
                    existing.surname = row["surname"]
                    existing.programme = row["programme"]
                    existing.year_level = row["year_level"]
                    updated += 1
                else:
                    user = lookup["users_by_email"][row["email"]]
                    db.add(StudentProfile(
                        user_id=user.id,
                        student_number=row["student_number"],
                        first_name=row["first_name"],
                        surname=row["surname"],
                        programme=row["programme"],
                        year_level=row["year_level"],
                    ))
                    created += 1
            elif dataset == "modules":
                existing = lookup["modules"].get(row["module_code"])
                if existing:
                    existing.module_name = row["module_name"]
                    existing.faculty = row["faculty"]
                    updated += 1
                else:
                    db.add(Module(
                        module_code=row["module_code"],
                        module_name=row["module_name"],
                        faculty=row["faculty"],
                    ))
                    created += 1
            elif dataset == "attendance":
                db.add(Attendance(
                    student_id=row["_student_id"],
                    module_id=row["_module_id"],
                    attendance_percentage=row["attendance_percentage"],
                    date=row["date"],
                ))
                created += 1
            else:
                db.add(Assessment(
                    student_id=row["_student_id"],
                    module_id=row["_module_id"],
                    assessment_type=row["assessment_type"],
                    mark=row["mark"],
                    assessment_date=row["assessment_date"],
                ))
                created += 1

        _audit_import(db, current_user, request, dataset, "SUCCESS")
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()
        _audit_import(db, current_user, request, dataset, "FAILURE")
        db.commit()
        logger.exception("csv_import_commit_failed", extra={"dataset": dataset, "user_id": current_user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CSV records could not be committed. No records were imported.",
        ) from error

    summary["persisted_rows"] = created + updated
    summary["created_rows"] = created
    summary["updated_rows"] = updated
    return summary


def _export_query(
    db: Session,
    dataset: str,
    student_number: Optional[str],
    module_code: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
):
    if dataset == "students":
        query = db.query(
            StudentProfile.student_number, User.email, StudentProfile.first_name, StudentProfile.surname,
            StudentProfile.programme, StudentProfile.year_level,
        ).join(User, User.id == StudentProfile.user_id)
        if student_number:
            query = query.filter(StudentProfile.student_number == student_number)
        return query.order_by(StudentProfile.student_number).yield_per(500)
    if dataset == "modules":
        query = db.query(Module.module_code, Module.module_name, Module.faculty)
        if module_code:
            query = query.filter(Module.module_code == module_code)
        return query.order_by(Module.module_code).yield_per(500)
    if dataset == "attendance":
        query = db.query(
            StudentProfile.student_number, Module.module_code, Attendance.attendance_percentage, Attendance.date,
        ).join(StudentProfile, StudentProfile.id == Attendance.student_id).join(Module, Module.id == Attendance.module_id)
        if student_number:
            query = query.filter(StudentProfile.student_number == student_number)
        if module_code:
            query = query.filter(Module.module_code == module_code)
        if date_from:
            query = query.filter(Attendance.date >= date_from)
        if date_to:
            query = query.filter(Attendance.date <= date_to)
        return query.order_by(Attendance.date, StudentProfile.student_number).yield_per(500)
    query = db.query(
        StudentProfile.student_number, Module.module_code, Assessment.assessment_type, Assessment.mark,
        Assessment.assessment_date,
    ).join(StudentProfile, StudentProfile.id == Assessment.student_id).join(Module, Module.id == Assessment.module_id)
    if student_number:
        query = query.filter(StudentProfile.student_number == student_number)
    if module_code:
        query = query.filter(Module.module_code == module_code)
    if date_from:
        query = query.filter(Assessment.assessment_date >= date_from)
    if date_to:
        query = query.filter(Assessment.assessment_date <= date_to)
    return query.order_by(Assessment.assessment_date, StudentProfile.student_number).yield_per(500)


def _lms_export_query(
    db: Session,
    dataset: str,
    student_id: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
    sheet_name: Optional[str],
):
    if dataset == "referrals":
        fields = tuple(getattr(Referral, field) for field in EXPORT_COLUMNS[dataset])
        query = db.query(*fields)
        if student_id:
            query = query.filter(Referral.student_id == student_id)
        if date_from:
            query = query.filter(func.date(Referral.created_at) >= date_from.isoformat())
        if date_to:
            query = query.filter(func.date(Referral.created_at) <= date_to.isoformat())
        return query.order_by(Referral.created_at, Referral.referral_id).yield_per(500)
    if dataset == "interventions":
        fields = tuple(getattr(Intervention, field) for field in EXPORT_COLUMNS[dataset])
        query = db.query(*fields)
        if student_id:
            query = query.filter(Intervention.student_id == student_id)
        if date_from:
            query = query.filter(func.date(Intervention.date_started) >= date_from.isoformat())
        if date_to:
            query = query.filter(func.date(Intervention.date_started) <= date_to.isoformat())
        return query.order_by(Intervention.created_at, Intervention.intervention_id).yield_per(500)
    if dataset == "meetings":
        fields = tuple(getattr(StudentMeeting, field) for field in EXPORT_COLUMNS[dataset])
        query = db.query(*fields)
        if student_id:
            query = query.filter(StudentMeeting.student_id == student_id)
        if date_from:
            query = query.filter(func.date(StudentMeeting.meeting_at) >= date_from.isoformat())
        if date_to:
            query = query.filter(func.date(StudentMeeting.meeting_at) <= date_to.isoformat())
        return query.order_by(StudentMeeting.meeting_at, StudentMeeting.meeting_id).yield_per(500)
    fields = tuple(getattr(WorkbookIntelligence, field) for field in EXPORT_COLUMNS[dataset])
    query = db.query(*fields)
    if sheet_name:
        query = query.filter(WorkbookIntelligence.sheet_name == sheet_name)
    return query.order_by(WorkbookIntelligence.sheet_name, WorkbookIntelligence.row_number).yield_per(500)


def _safe_cell(value: Any) -> Any:
    if hasattr(value, "value"):
        value = value.value
    if not isinstance(value, str):
        return value.isoformat() if hasattr(value, "isoformat") else value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _csv_chunks(rows: Any, columns: tuple[str, ...], selected: tuple[str, ...]):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(selected)
    yield "\ufeff" + buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    indexes = [columns.index(column) for column in selected]
    for row in rows:
        writer.writerow([_safe_cell(row[index]) for index in indexes])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


@router.get("/export/{dataset}")
def export_csv(
    dataset: ExportDataset,
    student_number: Optional[str] = Query(default=None, max_length=64),
    module_code: Optional[str] = Query(default=None, max_length=32),
    student_id: Optional[str] = Query(default=None, max_length=64),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    sheet_name: Optional[str] = Query(default=None, max_length=120),
    columns: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    schema = EXPORT_COLUMNS[dataset]
    selected = tuple(column.strip() for column in columns.split(",")) if columns else schema
    if not selected or len(set(selected)) != len(selected) or any(column not in schema for column in selected):
        raise HTTPException(status_code=422, detail="Requested columns are empty, duplicated, or unsupported.")
    core_datasets = ("students", "modules", "attendance", "assessments")
    lms_datasets = ("referrals", "interventions", "meetings", "workbook-intelligence")
    if dataset in ("students", "modules") and (
        (dataset == "students" and module_code) or (dataset == "modules" and student_number)
    ):
        raise HTTPException(status_code=422, detail="The supplied filter does not apply to this dataset.")
    if dataset in lms_datasets and (student_number or module_code):
        raise HTTPException(status_code=422, detail="Use the LMS student ID filter for this dataset.")
    if student_id and dataset not in ("referrals", "interventions", "meetings"):
        raise HTTPException(status_code=422, detail="Student ID filters are only supported for LMS case data.")
    if (date_from or date_to) and dataset not in ("attendance", "assessments", "referrals", "interventions", "meetings"):
        raise HTTPException(status_code=422, detail="Date filters are not supported for this dataset.")
    if sheet_name and dataset != "workbook-intelligence":
        raise HTTPException(status_code=422, detail="Sheet filters are only supported for workbook reports.")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="Start date must be on or before end date.")

    filename = f"neurosync-{dataset}.csv"
    if dataset in core_datasets:
        rows = iter(_export_query(db, dataset, student_number, module_code, date_from, date_to))
        first_row = next(rows, None)
        if first_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records matched the selected export filters.")
        return StreamingResponse(
            _csv_chunks(itertools.chain((first_row,), rows), schema, selected),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    lms_db = LMSSessionLocal()
    try:
        rows = iter(_lms_export_query(lms_db, dataset, student_id, date_from, date_to, sheet_name))
        first_row = next(rows, None)
        if first_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No records matched the selected export filters.")
        return StreamingResponse(
            _csv_chunks(itertools.chain((first_row,), rows), schema, selected),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            background=BackgroundTask(lms_db.close),
        )
    except Exception:
        lms_db.close()
        raise
