"""Import a weekly NeuroSync intelligence CSV without replacing LMS records."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from lms.database import CONFIGURED_LMS_DATABASE_URL, build_lms_session_factory
from lms.models import Student, WorkbookIntelligence

SHEET_NAME = "Weekly Intelligence"
REQUIRED_COLUMNS = {
    "student_id",
    "faculty",
    "programme",
    "enrolment_status",
    "risk_band",
    "report_week_start",
    "report_week_end",
    "retained_student",
    "logins_this_week",
    "login_days_this_week",
    "attendance_7d_scheduled",
    "attendance_7d_present",
    "attendance_7d_late",
    "attendance_7d_missed",
    "attendance_7d_pct",
    "attendance_30d_scheduled",
    "attendance_30d_present",
    "attendance_30d_late",
    "attendance_30d_missed",
    "attendance_30d_pct",
    "new_referrals_7d",
    "priority_referrals_7d",
    "high_risk_referrals_7d",
    "data_origin",
    "cohort_retention_rate_pct",
    "cohort_logins_this_week",
    "cohort_new_referrals_7d",
    "cohort_priority_referrals_7d",
    "cohort_high_risk_referrals_7d",
}
NONNEGATIVE_INTEGER_COLUMNS = {
    "logins_this_week",
    "login_days_this_week",
    "attendance_7d_scheduled",
    "attendance_7d_present",
    "attendance_7d_late",
    "attendance_7d_missed",
    "attendance_30d_scheduled",
    "attendance_30d_present",
    "attendance_30d_late",
    "attendance_30d_missed",
    "new_referrals_7d",
    "priority_referrals_7d",
    "high_risk_referrals_7d",
    "cohort_logins_this_week",
    "cohort_new_referrals_7d",
    "cohort_priority_referrals_7d",
    "cohort_high_risk_referrals_7d",
}
PERCENTAGE_COLUMNS = {
    "attendance_7d_pct",
    "attendance_30d_pct",
    "cohort_retention_rate_pct",
}


def _read_weekly_csv(path: Path) -> tuple[str, list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no CSV header row")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path.name} contains duplicate column names")
        missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing_columns:
            raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing_columns))}")
        rows = list(reader)

    if not rows:
        raise ValueError(f"{path.name} contains no student rows")
    if any(None in row for row in rows):
        raise ValueError(f"{path.name} contains rows with more values than its header")

    week_start = rows[0]["report_week_start"]
    week_end = rows[0]["report_week_end"]
    if not week_start or not week_end:
        raise ValueError("report_week_start and report_week_end are required")
    try:
        start_date = date.fromisoformat(week_start)
        end_date = date.fromisoformat(week_end)
    except ValueError as error:
        raise ValueError("Report week dates must use YYYY-MM-DD format") from error
    if start_date > end_date:
        raise ValueError("report_week_start must not be later than report_week_end")

    student_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        missing_values = sorted(
            column for column in REQUIRED_COLUMNS
            if row.get(column) is None or not row[column].strip()
        )
        if missing_values:
            raise ValueError(f"Row {row_number}: required values are missing for {', '.join(missing_values)}")
        student_id = row["student_id"].strip()
        if not student_id:
            raise ValueError(f"Row {row_number}: student_id is required")
        if student_id in student_ids:
            raise ValueError(f"Duplicate student_id {student_id!r} in {path.name}")
        student_ids.add(student_id)
        if row["report_week_start"] != week_start or row["report_week_end"] != week_end:
            raise ValueError(f"Row {row_number}: all records must cover the same report week")
        if row["risk_band"].strip().lower() not in {"low", "medium", "high"}:
            raise ValueError(f"Row {row_number}: risk_band must be Low, Medium, or High")
        if row["retained_student"].strip() not in {"0", "1"}:
            raise ValueError(f"Row {row_number}: retained_student must be 0 or 1")
        for column in NONNEGATIVE_INTEGER_COLUMNS:
            try:
                value = int(row[column])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Row {row_number}: {column} must be a non-negative integer") from error
            if value < 0:
                raise ValueError(f"Row {row_number}: {column} must be a non-negative integer")
        for column in PERCENTAGE_COLUMNS:
            try:
                value = float(row[column])
            except (TypeError, ValueError) as error:
                raise ValueError(f"Row {row_number}: {column} must be between 0 and 100") from error
            if not 0 <= value <= 100:
                raise ValueError(f"Row {row_number}: {column} must be between 0 and 100")

    return week_start, rows


def import_weekly_intelligence(
    csv_path: str | Path,
    database_url: str | None = None,
) -> dict[str, int | str]:
    """Upsert one weekly report while preserving the existing LMS dataset."""
    source = Path(csv_path)
    week_start, rows = _read_weekly_csv(source)
    engine, session_factory = build_lms_session_factory(database_url=database_url)
    db = session_factory()
    try:
        known_student_ids = {
            student_id for (student_id,) in db.query(Student.student_id).all()
        }
        unknown_student_ids = sorted(
            {row["student_id"].strip() for row in rows}.difference(known_student_ids)
        )
        if unknown_student_ids:
            preview = ", ".join(unknown_student_ids[:5])
            raise ValueError(f"Weekly report references unknown students: {preview}")

        prefix = f"weekly-intelligence:{week_start}:"
        current_ids = {f"{prefix}{row['student_id'].strip()}" for row in rows}
        existing = {
            record.record_id: record
            for record in db.query(WorkbookIntelligence)
            .filter(WorkbookIntelligence.record_id.like(f"{prefix}%"))
            .all()
        }
        for record_id, record in existing.items():
            if record_id not in current_ids:
                db.delete(record)

        for row_number, row in enumerate(rows, start=2):
            student_id = row["student_id"].strip()
            record_id = f"{prefix}{student_id}"
            record = existing.get(record_id)
            if record is None:
                record = WorkbookIntelligence(record_id=record_id, sheet_name=SHEET_NAME, row_number=row_number)
                db.add(record)
            record.sheet_name = SHEET_NAME
            record.row_number = row_number
            record.payload = json.dumps(row, ensure_ascii=True, sort_keys=True)

        db.commit()
        return {"report_week_start": week_start, "student_count": len(rows)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a weekly intelligence CSV without replacing the LMS dataset.")
    parser.add_argument("csv_path", help="Path to NeuroSync_Weekly_Intelligence CSV")
    parser.add_argument(
        "--database-url",
        default=CONFIGURED_LMS_DATABASE_URL,
        help="Target LMS database URL; defaults to the configured LMS database.",
    )
    args = parser.parse_args()
    print(import_weekly_intelligence(args.csv_path, args.database_url))


if __name__ == "__main__":
    main()
