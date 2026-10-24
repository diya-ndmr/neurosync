"""Import the separate synthetic 100-student contact and advisor CSV dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from lms.database import CONFIGURED_LMS_DATABASE_URL, build_lms_session_factory
from lms.models import DatasetSourceRow

FILES = {
    "advisor_actions.csv": {"action_id", "student_id", "referral_id", "action_type", "due_date", "status", "priority"},
    "advisor_interventions.csv": {"intervention_id", "student_id", "referral_id", "support_strategy", "start_date", "review_date", "status", "follow_up_due"},
    "advisor_referrals.csv": {"referral_id", "student_id", "advisor_id", "risk_level", "reason", "urgency", "status", "created_date", "next_follow_up", "consent_status"},
    "neurosync_all_100_students_combined.csv": {"student_id", "risk_level", "assigned_advisor", "attendance_percent", "average_mark", "referral_count", "intervention_count", "advisor_action_count", "support_request_count"},
    "students_100_with_contacts.csv": {"student_id", "first_name", "surname", "phone_number", "email", "faculty", "risk_level", "assigned_advisor", "attendance_percent", "average_mark", "last_lms_login"},
    "student_support_requests.csv": {"request_id", "student_id", "request_type", "submitted_date", "status", "assigned_advisor"},
}
IDENTIFIER_COLUMNS = {
    "advisor_actions.csv": "action_id",
    "advisor_interventions.csv": "intervention_id",
    "advisor_referrals.csv": "referral_id",
    "neurosync_all_100_students_combined.csv": "student_id",
    "students_100_with_contacts.csv": "student_id",
    "student_support_requests.csv": "request_id",
}


def _read_files(source_dir: Path) -> dict[str, list[dict[str, str]]]:
    rows_by_file = {}
    for filename, required_columns in FILES.items():
        path = source_dir / filename
        if not path.is_file():
            raise ValueError(f"Required CSV file is missing: {filename}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError(f"{filename} has no CSV header row")
            missing = required_columns.difference(reader.fieldnames)
            if missing:
                raise ValueError(f"{filename} is missing columns: {', '.join(sorted(missing))}")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError(f"{filename} contains duplicate column names")
            rows = list(reader)
        if not rows:
            raise ValueError(f"{filename} contains no data rows")
        if any(None in row for row in rows):
            raise ValueError(f"{filename} contains a row with more values than its header")
        identifier_column = IDENTIFIER_COLUMNS[filename]
        identifiers = [row.get(identifier_column, "").strip() for row in rows]
        if any(not identifier for identifier in identifiers):
            raise ValueError(f"{filename}.{identifier_column} cannot be blank")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError(f"{filename} contains duplicate {identifier_column} values")
        rows_by_file[filename] = rows

    master_ids = {row["student_id"].strip() for row in rows_by_file["students_100_with_contacts.csv"]}
    combined_ids = {row["student_id"].strip() for row in rows_by_file["neurosync_all_100_students_combined.csv"]}
    if master_ids != combined_ids:
        raise ValueError("The student and combined CSVs must contain the same student IDs")
    for filename in ("advisor_referrals.csv", "advisor_interventions.csv", "advisor_actions.csv", "student_support_requests.csv"):
        unknown = sorted({row["student_id"].strip() for row in rows_by_file[filename]} - master_ids)
        if unknown:
            raise ValueError(f"{filename} references unknown students: {', '.join(unknown[:5])}")
    referral_ids = {row["referral_id"].strip() for row in rows_by_file["advisor_referrals.csv"]}
    for filename in ("advisor_interventions.csv", "advisor_actions.csv"):
        unknown = sorted({row["referral_id"].strip() for row in rows_by_file[filename]} - referral_ids)
        if unknown:
            raise ValueError(f"{filename} references unknown referrals: {', '.join(unknown[:5])}")

    return rows_by_file


def import_contact_demo_dataset(
    source_dir: str | Path,
    database_url: str | None = None,
) -> dict[str, int | str]:
    """Replace only this import's source rows; preserve the active LMS records."""
    directory = Path(source_dir).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("CSV source path must be a directory")
    rows_by_file = _read_files(directory)
    digest = hashlib.sha256()
    for filename in sorted(FILES):
        digest.update(filename.encode("utf-8"))
        digest.update((directory / filename).read_bytes())
    dataset_key = digest.hexdigest()[:16]

    engine, session_factory = build_lms_session_factory(database_url=database_url)
    db = session_factory()
    try:
        prefix = "contact-demo:"
        existing = db.query(DatasetSourceRow).filter(
            DatasetSourceRow.source_row_id.like(f"{prefix}%")
        ).all()
        for row in existing:
            db.delete(row)

        for filename, rows in rows_by_file.items():
            identifier_column = IDENTIFIER_COLUMNS[filename]
            for row_number, data in enumerate(rows, start=2):
                identifier = data[identifier_column].strip()
                if not identifier:
                    raise ValueError(f"{filename}.{identifier_column} cannot be blank")
                db.add(DatasetSourceRow(
                    source_row_id=f"{prefix}{dataset_key}:{filename}:{identifier}",
                    source_name=filename,
                    row_number=row_number,
                    payload=json.dumps(data, ensure_ascii=True, sort_keys=True),
                ))
        db.commit()
        return {
            "status": "imported",
            "dataset": "contact-demo",
            "student_count": len(rows_by_file["students_100_with_contacts.csv"]),
            "combined_summary_count": len(rows_by_file["neurosync_all_100_students_combined.csv"]),
            "referral_count": len(rows_by_file["advisor_referrals.csv"]),
            "intervention_count": len(rows_by_file["advisor_interventions.csv"]),
            "action_count": len(rows_by_file["advisor_actions.csv"]),
            "support_request_count": len(rows_by_file["student_support_requests.csv"]),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the separate synthetic contact and advisor CSV dataset.")
    parser.add_argument("source_dir", help="Directory containing the six NeuroSync CSV files")
    parser.add_argument("--database-url", default=CONFIGURED_LMS_DATABASE_URL)
    args = parser.parse_args()
    print(import_contact_demo_dataset(args.source_dir, args.database_url))


if __name__ == "__main__":
    main()
