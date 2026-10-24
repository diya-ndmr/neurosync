import csv
import json

import pytest

from lms.contact_demo_import import FILES, import_contact_demo_dataset
from lms.database import LMSBase, build_lms_session_factory
from lms.models import DatasetSourceRow, Programme, Student


def _write_dataset(folder):
    folder.mkdir(parents=True)
    rows = {
        "students_100_with_contacts.csv": {
            "student_id": "STU001", "first_name": "Sam", "surname": "Example",
            "phone_number": "000", "email": "sam@example.test", "student_name": "Sam Example",
            "faculty": "Computing", "risk_level": "Medium", "assigned_advisor": "ADV01",
            "attendance_percent": "80", "average_mark": "65", "last_lms_login": "2026-10-20",
        },
        "neurosync_all_100_students_combined.csv": {
            "student_id": "STU001", "risk_level": "Medium", "assigned_advisor": "ADV01",
            "attendance_percent": "80", "average_mark": "65", "referral_count": "1",
            "intervention_count": "1", "advisor_action_count": "1", "support_request_count": "1",
        },
        "advisor_referrals.csv": {
            "student_id": "STU001", "first_name": "Sam", "surname": "Example", "phone_number": "000",
            "email": "sam@example.test", "referral_id": "REF001", "advisor_id": "ADV01",
            "risk_level": "Medium", "reason": "Check in", "urgency": "High", "status": "New",
            "created_date": "2026-10-20", "next_follow_up": "", "consent_status": "Demo only", "notes": "",
        },
        "advisor_interventions.csv": {
            "student_id": "STU001", "first_name": "Sam", "surname": "Example", "phone_number": "000",
            "email": "sam@example.test", "intervention_id": "INT001", "referral_id": "REF001",
            "advisor_id": "ADV01", "support_strategy": "Study support", "start_date": "2026-10-20",
            "review_date": "", "status": "Planned", "follow_up_due": "", "advisor_notes": "", "last_updated": "",
        },
        "advisor_actions.csv": {
            "student_id": "STU001", "first_name": "Sam", "surname": "Example", "phone_number": "000",
            "email": "sam@example.test", "action_id": "ACT001", "referral_id": "REF001",
            "advisor_id": "ADV01", "action_type": "Follow-up", "due_date": "2026-10-27",
            "status": "Open", "priority": "High",
        },
        "student_support_requests.csv": {
            "student_id": "STU001", "first_name": "Sam", "surname": "Example",
            "phone_number": "000", "email": "sam@example.test", "request_id": "REQ001",
            "request_type": "Study support", "submitted_date": "2026-10-20",
            "status": "Open", "assigned_advisor": "ADV01",
        },
    }
    for filename in FILES:
        values = rows[filename]
        path = folder / filename
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=values)
            writer.writeheader()
            writer.writerow(values)
    return folder


def test_contact_demo_import_preserves_lms_records_and_replaces_own_rows(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'contact-demo.db'}"
    engine, factory = build_lms_session_factory(database_url=database_url)
    LMSBase.metadata.create_all(engine)
    db = factory()
    db.add(Programme(
        programme_id="P001", programme_code="CS", programme_name="Computing",
        faculty="Computing", level="Undergraduate",
    ))
    db.add(Student(
        student_id="ST0001", first_name="Existing", surname="Student",
        institutional_email="existing@example.test", programme_id="P001",
        year_of_study=1, semester=1,
    ))
    db.commit()
    db.close()
    engine.dispose()

    folder = _write_dataset(tmp_path / "source")
    result = import_contact_demo_dataset(folder, database_url)
    assert result == {
        "status": "imported",
        "dataset": "contact-demo",
        "student_count": 1,
        "combined_summary_count": 1,
        "referral_count": 1,
        "intervention_count": 1,
        "action_count": 1,
        "support_request_count": 1,
    }

    result = import_contact_demo_dataset(folder, database_url)
    assert result["student_count"] == 1

    engine, factory = build_lms_session_factory(database_url=database_url)
    db = factory()
    try:
        assert db.query(Student).count() == 1
        records = db.query(DatasetSourceRow).filter(DatasetSourceRow.source_row_id.like("contact-demo:%")).all()
        assert len(records) == len(FILES)
        students = [row for row in records if row.source_name == "students_100_with_contacts.csv"]
        assert json.loads(students[0].payload)["student_id"] == "STU001"
    finally:
        db.close()
        engine.dispose()


def test_contact_demo_import_rejects_unknown_referral_student(tmp_path):
    folder = _write_dataset(tmp_path / "source")
    path = folder / "advisor_referrals.csv"
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
        fields = rows[0].keys()
    rows[0]["student_id"] = "STU999"
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="advisor_referrals.csv references unknown students"):
        import_contact_demo_dataset(folder, f"sqlite:///{tmp_path / 'invalid.db'}")
