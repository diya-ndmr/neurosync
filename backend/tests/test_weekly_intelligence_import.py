import csv

import pytest

from lms.database import LMSBase, build_lms_session_factory
from lms.models import Programme, Student, WorkbookIntelligence
from lms.weekly_intelligence_import import import_weekly_intelligence


def _write_weekly_csv(path, rows):
    fieldnames = [
        "student_id", "faculty", "programme", "enrolment_status", "risk_band",
        "report_week_start", "report_week_end", "retained_student",
        "logins_this_week", "login_days_this_week", "attendance_7d_scheduled",
        "attendance_7d_present", "attendance_7d_late", "attendance_7d_missed",
        "attendance_7d_pct", "attendance_30d_scheduled", "attendance_30d_present",
        "attendance_30d_late", "attendance_30d_missed", "attendance_30d_pct",
        "new_referrals_7d", "priority_referrals_7d", "high_risk_referrals_7d",
        "data_origin", "cohort_retention_rate_pct", "cohort_logins_this_week",
        "cohort_new_referrals_7d", "cohort_priority_referrals_7d",
        "cohort_high_risk_referrals_7d",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _row(student_id="ST0001", logins="5"):
    return {
        "student_id": student_id,
        "faculty": "Information Technology",
        "programme": "Data Science",
        "enrolment_status": "Active",
        "risk_band": "Low",
        "report_week_start": "2026-10-13",
        "report_week_end": "2026-10-19",
        "retained_student": "1",
        "logins_this_week": logins,
        "login_days_this_week": "2",
        "attendance_7d_scheduled": "3",
        "attendance_7d_present": "3",
        "attendance_7d_late": "0",
        "attendance_7d_missed": "0",
        "attendance_7d_pct": "100.0",
        "attendance_30d_scheduled": "12",
        "attendance_30d_present": "11",
        "attendance_30d_late": "0",
        "attendance_30d_missed": "1",
        "attendance_30d_pct": "91.7",
        "new_referrals_7d": "0",
        "priority_referrals_7d": "0",
        "high_risk_referrals_7d": "0",
        "data_origin": "Synthetic weekly extension",
        "cohort_retention_rate_pct": "100.0",
        "cohort_logins_this_week": "3262",
        "cohort_new_referrals_7d": "37",
        "cohort_priority_referrals_7d": "11",
        "cohort_high_risk_referrals_7d": "9",
    }


def test_weekly_import_preserves_lms_and_upserts_same_report_week(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'weekly.db'}"
    engine, factory = build_lms_session_factory(database_url=database_url)
    LMSBase.metadata.create_all(engine)
    db = factory()
    try:
        db.add(Programme(
            programme_id="P001",
            programme_code="DS",
            programme_name="Data Science",
            faculty="Information Technology",
            level="Undergraduate",
        ))
        db.add(Student(
            student_id="ST0001",
            first_name="Sam",
            surname="Student",
            institutional_email="sam@example.test",
            programme_id="P001",
            year_of_study=1,
            semester=1,
        ))
        db.commit()
    finally:
        db.close()
        engine.dispose()

    csv_path = _write_weekly_csv(tmp_path / "weekly.csv", [_row()])
    assert import_weekly_intelligence(csv_path, database_url) == {
        "report_week_start": "2026-10-13",
        "student_count": 1,
    }
    _write_weekly_csv(csv_path, [_row(logins="7")])
    import_weekly_intelligence(csv_path, database_url)

    engine, factory = build_lms_session_factory(database_url=database_url)
    db = factory()
    try:
        assert db.query(Student).count() == 1
        records = db.query(WorkbookIntelligence).all()
        assert len(records) == 1
        assert records[0].row_number == 2
        assert '"logins_this_week": "7"' in records[0].payload
    finally:
        db.close()
        engine.dispose()


def test_weekly_import_rejects_unknown_students_without_writing_records(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'weekly.db'}"
    engine, _ = build_lms_session_factory(database_url=database_url)
    LMSBase.metadata.create_all(engine)
    engine.dispose()
    csv_path = _write_weekly_csv(tmp_path / "weekly.csv", [_row(student_id="ST9999")])

    with pytest.raises(ValueError, match="unknown students"):
        import_weekly_intelligence(csv_path, database_url)


def test_weekly_import_rejects_mixed_report_weeks(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'weekly.db'}"
    engine, _ = build_lms_session_factory(database_url=database_url)
    LMSBase.metadata.create_all(engine)
    engine.dispose()
    second_row = _row(student_id="ST0002")
    second_row["report_week_start"] = "2026-10-14"
    csv_path = _write_weekly_csv(tmp_path / "weekly.csv", [_row(), second_row])

    with pytest.raises(ValueError, match="same report week"):
        import_weekly_intelligence(csv_path, database_url)


def test_weekly_import_rejects_blank_required_values(tmp_path):
    row = _row()
    row["risk_band"] = ""
    csv_path = _write_weekly_csv(tmp_path / "weekly.csv", [row])

    with pytest.raises(ValueError, match="risk_band"):
        import_weekly_intelligence(csv_path, "sqlite:///unused.db")
