import csv
import io
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api import csv_data
from app.database.connection import Base, get_db
from app.middleware.security import get_current_user
from app.models.assessment import Assessment
from app.models.audit_event import AuditEvent
from app.models.attendance import Attendance
from app.models.csv_import_history import CsvImportHistory
from app.models.module import Module
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from lms.database import LMSBase
from lms.models import (
    Intervention,
    Lecturer,
    Module as LMSModule,
    Programme,
    Referral,
    Student as LMSStudent,
    StudentMeeting,
    WorkbookIntelligence,
)

STUDENT_HEADERS = "student_number,email,first_name,surname,programme,year_level"
ATTENDANCE_HEADERS = "student_number,module_code,attendance_percentage,date"
ASSESSMENT_HEADERS = "student_number,module_code,assessment_type,mark,assessment_date"
MODULE_HEADERS = "module_code,module_name,faculty"


def csv_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def upload(client: TestClient, dataset: str, content: bytes, *, preview: bool = False, mode: str = "create"):
    suffix = "/preview" if preview else ""
    return client.post(
        f"/api/admin/csv/import/{dataset}{suffix}",
        params={"mode": mode},
        files={"file": ("records.csv", content, "text/csv")},
    )


@pytest.fixture
def csv_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'csv-api.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        admin = User(
            id="admin-1", email="admin@example.edu", password_hash="test-hash",
            name="Admin", role=UserRole.admin,
        )
        existing_user = User(
            id="student-user-1", email="student@example.edu", password_hash="test-hash",
            name="Existing Student", role=UserRole.student,
        )
        new_user = User(
            id="student-user-2", email="newstudent@example.edu", password_hash="test-hash",
            name="New Student", role=UserRole.student,
        )
        db.add_all([admin, existing_user, new_user])
        db.flush()
        db.add_all([
            StudentProfile(
                id="student-1", user_id=existing_user.id, student_number="STU001",
                first_name="Avery", surname="One", programme="Computing", year_level=2,
            ),
            Module(id="module-1", module_code="COMP101", module_name="Computing", faculty="Science"),
        ])
        db.commit()

    actor = {"user": SimpleNamespace(id="admin-1", email="admin@example.edu", role=UserRole.admin)}

    def override_get_db():
        with factory() as db:
            yield db

    app = FastAPI()
    app.include_router(csv_data.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: actor["user"]
    client = TestClient(app)
    client.session_factory = factory  # type: ignore[attr-defined]
    client.engine = engine  # type: ignore[attr-defined]
    client.act_as = lambda user: actor.update({
        "user": SimpleNamespace(id=user.id, email=user.email, role=user.role),
    })  # type: ignore[attr-defined]
    yield client
    client.close()
    engine.dispose()


def test_csv_catalog_requires_admin_and_lists_import_contract(csv_client):
    catalog = csv_client.get("/api/admin/csv/datasets")
    assert catalog.status_code == 200
    assert catalog.json()["import"]["attendance"]["columns"] == [
        "student_number", "module_code", "attendance_percentage", "date",
    ]
    assert catalog.json()["max_file_bytes"] == csv_data.MAX_CSV_FILE_BYTES

    csv_client.act_as(User(
        id="lecturer-1", email="lecturer@example.edu", password_hash="x", name="Lecturer", role=UserRole.lecturer,
    ))
    assert csv_client.get("/api/admin/csv/datasets").status_code == 403
    assert csv_client.get("/api/admin/csv/export/students").status_code == 403
    assert upload(csv_client, "students", csv_bytes(STUDENT_HEADERS + "\nSTU002,newstudent@example.edu,New,Student,Computing,1")).status_code == 403
    csv_client.app.dependency_overrides.pop(get_current_user)  # type: ignore[attr-defined]
    assert csv_client.get("/api/admin/csv/datasets").status_code == 401


def test_student_import_preview_create_update_and_explicit_upsert(csv_client):
    content = csv_bytes(STUDENT_HEADERS + "\nSTU002,newstudent@example.edu,Renée,Student,Computing,1\n")
    preview = upload(csv_client, "students", content, preview=True)
    assert preview.status_code == 200
    assert preview.json()["valid_rows"] == 1
    assert preview.json()["persisted_rows"] == 0
    with csv_client.session_factory() as db:
        assert db.query(StudentProfile).filter_by(student_number="STU002").count() == 0

    created = upload(csv_client, "students", content)
    assert created.status_code == 200, created.text
    assert created.json()["created_rows"] == 1

    duplicate = upload(csv_client, "students", content)
    assert duplicate.status_code == 422
    assert duplicate.json()["detail"]["duplicate_rows"] == 1

    update_content = csv_bytes(STUDENT_HEADERS + "\nSTU002,newstudent@example.edu,Renée,Changed,Data Science,3\n")
    updated = upload(csv_client, "students", update_content, mode="upsert")
    assert updated.status_code == 200, updated.text
    assert updated.json()["updated_rows"] == 1
    with csv_client.session_factory() as db:
        profile = db.query(StudentProfile).filter_by(student_number="STU002").one()
        assert (profile.surname, profile.programme, profile.year_level) == ("Changed", "Data Science", 3)
        assert db.query(StudentProfile).count() == 2
        history = db.query(CsvImportHistory).all()
        assert any(item.outcome == "SUCCESS" and item.persisted_rows == 1 for item in history)
        assert any(item.outcome == "REJECTED" and item.errors for item in history)


def test_module_import_supports_create_and_explicit_update(csv_client):
    created = upload(csv_client, "modules", csv_bytes(MODULE_HEADERS + "\nMATH201,Mathematics,Science\n"))
    assert created.status_code == 200, created.text
    duplicate = upload(csv_client, "modules", csv_bytes(MODULE_HEADERS + "\nMATH201,Other,Science\n"))
    assert duplicate.status_code == 422
    updated = upload(
        csv_client,
        "modules",
        csv_bytes(MODULE_HEADERS + "\nmath201,Advanced mathematics,Computing\n"),
        mode="update",
    )
    assert updated.status_code == 200, updated.text
    with csv_client.session_factory() as db:
        module = db.query(Module).filter_by(module_code="MATH201").one()
        assert module.module_name == "Advanced mathematics"
        assert db.query(Module).count() == 2


@pytest.mark.parametrize(
    ("dataset", "headers", "row", "expected_code"),
    [
        ("attendance", ATTENDANCE_HEADERS, "STU001,COMP101,101,2026-01-01", "invalid_number"),
        ("attendance", ATTENDANCE_HEADERS, "STU001,COMP101,80,not-a-date", "invalid_date"),
        ("attendance", ATTENDANCE_HEADERS, "STU001,COMP101,80,", "missing_value"),
        ("assessments", ASSESSMENT_HEADERS, "STU001,COMP101,Exam,NaN,2026-01-01", "invalid_number"),
        ("assessments", ASSESSMENT_HEADERS, "STU001,COMP101,Exam,90,2026-02-30", "invalid_date"),
        ("students", STUDENT_HEADERS, "STU002,not-an-email,New,Student,Computing,1", "invalid_email"),
    ],
)
def test_import_rejects_invalid_typed_values(csv_client, dataset, headers, row, expected_code):
    response = upload(csv_client, dataset, csv_bytes(headers + "\n" + row), preview=True)
    assert response.status_code == 200
    assert response.json()["valid_rows"] == 0
    assert response.json()["invalid_rows"] == 1
    assert expected_code in {error["code"] for error in response.json()["errors"]}


def test_attendance_and_assessment_import_persist_and_reject_duplicates(csv_client):
    attendance_csv = csv_bytes(ATTENDANCE_HEADERS + "\nSTU001,COMP101,87.5,2026-04-12\n")
    preview = upload(csv_client, "attendance", attendance_csv, preview=True)
    assert preview.status_code == 200 and preview.json()["valid_rows"] == 1
    imported = upload(csv_client, "attendance", attendance_csv)
    assert imported.status_code == 200, imported.text
    duplicate = upload(csv_client, "attendance", attendance_csv)
    assert duplicate.status_code == 422

    assessment_csv = csv_bytes(ASSESSMENT_HEADERS + "\nSTU001,COMP101,Exam,91,2026-04-12\n")
    assessment = upload(csv_client, "assessments", assessment_csv)
    assert assessment.status_code == 200, assessment.text
    with csv_client.session_factory() as db:
        assert db.query(Attendance).count() == 1
        assert db.query(Assessment).count() == 1
        assert db.query(AuditEvent).filter_by(action="CSV_IMPORT_ATTENDANCE", outcome="SUCCESS").count() == 1


def test_invalid_headers_duplicate_rows_and_conflicting_references(csv_client):
    missing_header = upload(csv_client, "students", csv_bytes("student_number,email\nSTU002,newstudent@example.edu\n"), preview=True)
    assert missing_header.status_code == 200
    assert "missing_header" in {error["code"] for error in missing_header.json()["errors"]}

    duplicate_header = upload(
        csv_client,
        "modules",
        csv_bytes("module_code,module_code,faculty\nMATH201,MATH202,Science\n"),
        preview=True,
    )
    assert "duplicate_header" in {error["code"] for error in duplicate_header.json()["errors"]}

    duplicate_rows = upload(
        csv_client,
        "modules",
        csv_bytes(MODULE_HEADERS + "\nMATH201,Math,Science\nmath201,Other,Computing\n"),
        preview=True,
    )
    assert duplicate_rows.json()["duplicate_rows"] == 1

    unknown_student = upload(
        csv_client,
        "attendance",
        csv_bytes(ATTENDANCE_HEADERS + "\nSTU404,COMP101,90,2026-04-12\n"),
        preview=True,
    )
    assert "unknown_student" in {error["code"] for error in unknown_student.json()["errors"]}

    unknown_module = upload(
        csv_client,
        "assessments",
        csv_bytes(ASSESSMENT_HEADERS + "\nSTU001,NOPE,Exam,90,2026-04-12\n"),
        preview=True,
    )
    assert "unknown_module" in {error["code"] for error in unknown_module.json()["errors"]}


@pytest.mark.parametrize(
    ("filename", "content", "expected_status"),
    [
        ("records.txt", b"not csv", 415),
        ("records.csv", b"", 422),
        ("records.csv", b"\xff\xfe", 200),
        ("records.csv", b"module_code,module_name,faculty\nMATH201,\"unclosed,Science\n", 200),
    ],
)
def test_upload_file_type_empty_encoding_and_malformed_csv(csv_client, filename, content, expected_status):
    response = csv_client.post(
        "/api/admin/csv/import/modules/preview",
        files={"file": (filename, content, "text/csv")},
    )
    assert response.status_code == expected_status
    if content == b"\xff\xfe":
        assert response.json()["errors"][0]["code"] == "encoding"
    if b"unclosed" in content:
        assert response.json()["errors"][0]["code"] == "malformed_csv"


def test_upload_size_limit_and_formula_injection_are_rejected(csv_client):
    too_large = b"module_code,module_name,faculty\n" + b"x" * csv_data.MAX_CSV_FILE_BYTES
    response = upload(csv_client, "modules", too_large, preview=True)
    assert response.status_code == 413

    formula = upload(
        csv_client,
        "modules",
        csv_bytes(MODULE_HEADERS + "\nMATH201,=HYPERLINK(\"https://example.invalid\"),Science\n"),
        preview=True,
    )
    assert formula.status_code == 200
    assert "unsafe_formula" in {error["code"] for error in formula.json()["errors"]}

    too_many_rows = csv_bytes(MODULE_HEADERS + "\n" + "\n".join(
        f"MOD{index},Module {index},Science" for index in range(csv_data.MAX_CSV_ROWS + 1)
    ))
    limited = upload(csv_client, "modules", too_many_rows, preview=True)
    assert limited.status_code == 200
    assert limited.json()["valid_rows"] == 0
    assert "row_limit" in {error["code"] for error in limited.json()["errors"]}


def test_import_is_atomic_when_persistence_fails(csv_client, monkeypatch):
    from sqlalchemy.orm import Session

    original_commit = Session.commit
    calls = {"count": 0}

    def fail_first_commit(session):
        calls["count"] += 1
        if calls["count"] == 1:
            raise SQLAlchemyError("test transaction failure")
        return original_commit(session)

    monkeypatch.setattr(Session, "commit", fail_first_commit)
    response = upload(
        csv_client,
        "modules",
        csv_bytes(MODULE_HEADERS + "\nMATH201,Mathematics,Science\n"),
    )
    assert response.status_code == 500
    with csv_client.session_factory() as db:
        assert db.query(Module).count() == 1
        assert db.query(AuditEvent).filter_by(action="CSV_IMPORT_MODULES", outcome="FAILURE").count() == 1


def test_export_is_filtered_escaped_utf8_and_round_trips(csv_client):
    with csv_client.session_factory() as db:
        profile = db.query(StudentProfile).filter_by(student_number="STU001").one()
        profile.first_name = 'A, "Quoted"\nNáme'
        db.add(Attendance(
            student_id="student-1", module_id="module-1", attendance_percentage=88.5, date=date(2026, 4, 12),
        ))
        db.add(Attendance(
            student_id="student-1", module_id="module-1", attendance_percentage=70, date=date(2026, 5, 12),
        ))
        db.add(Assessment(
            student_id="student-1", module_id="module-1", assessment_type="Exam", mark=93,
            assessment_date=date(2026, 4, 12),
        ))
        db.commit()

    response = csv_client.get(
        "/api/admin/csv/export/attendance",
        params={"student_number": "STU001", "date_from": "2026-04-01", "date_to": "2026-04-30"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=\"neurosync-attendance.csv\"" == response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"), newline="")))
    assert rows == [
        ["student_number", "module_code", "attendance_percentage", "date"],
        ["STU001", "COMP101", "88.5", "2026-04-12"],
    ]

    student_export = csv_client.get("/api/admin/csv/export/students", params={"columns": "student_number,email,first_name,surname,programme,year_level"})
    assert "Náme".encode("utf-8") in student_export.content
    round_trip = upload(csv_client, "students", student_export.content, mode="upsert")
    assert round_trip.status_code == 200, round_trip.text
    with csv_client.session_factory() as db:
        profile = db.query(StudentProfile).filter_by(student_number="STU001").one()
        assert profile.first_name == 'A, "Quoted"\nNáme'
        assert db.query(StudentProfile).count() == 1
        assert db.query(Attendance).count() == 2

    attendance_export = csv_client.get("/api/admin/csv/export/attendance", params={
        "student_number": "STU001", "date_from": "2026-04-01", "date_to": "2026-04-30",
    })
    replay = upload(csv_client, "attendance", attendance_export.content)
    assert replay.status_code == 422
    assert replay.json()["detail"]["duplicate_rows"] == 1
    with csv_client.session_factory() as db:
        assert db.query(Attendance).count() == 2


def test_export_formula_values_are_neutralized_and_columns_are_checked(csv_client):
    with csv_client.session_factory() as db:
        profile = db.query(StudentProfile).filter_by(student_number="STU001").one()
        profile.first_name = "=HYPERLINK(\"https://example.invalid\")"
        db.commit()

    response = csv_client.get("/api/admin/csv/export/students", params={"columns": "student_number,first_name"})
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"), newline="")))
    assert rows[1][1].startswith("'=")
    assert csv_client.get("/api/admin/csv/export/students", params={"columns": "email,unknown"}).status_code == 422
    assert csv_client.get(
        "/api/admin/csv/export/assessments", params={"date_from": "2026-05-01", "date_to": "2026-04-01"},
    ).status_code == 422


def test_lms_exports_use_persisted_rows_and_filters(tmp_path, csv_client, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'lms-export.db'}", connect_args={"check_same_thread": False})
    LMSBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as db:
        db.add(Programme(
            programme_id="programme-1", programme_code="EXP001", programme_name="Export programme",
            faculty="Computing", level="Undergraduate",
        ))
        db.add(Lecturer(
            lecturer_id="lecturer-1", first_name="Riley", surname="Lecturer",
            email="riley@example.edu", department="Computing",
        ))
        db.flush()
        db.add_all([
            LMSStudent(
                student_id="lms-student-1", first_name="Casey", surname="Student",
                institutional_email="casey@example.edu", programme_id="programme-1",
                year_of_study=1, semester=1,
            ),
            LMSStudent(
                student_id="lms-student-2", first_name="Jordan", surname="Student",
                institutional_email="jordan@example.edu", programme_id="programme-1",
                year_of_study=1, semester=1,
            ),
        ])
        db.add(LMSModule(
            module_id="lms-module-1", programme_id="programme-1", module_code="EXP101",
            module_name="Export module", credits=15, semester=1, lecturer_id="lecturer-1",
        ))
        db.flush()
        db.add_all([
            Referral(
                referral_id="referral-1", student_id="lms-student-1", lecturer_id="lecturer-1",
                module_id="lms-module-1", risk_level="HIGH", risk_score=0.9,
                reason='Concern, with "quotes"\nand another line', urgency="HIGH",
            ),
            Referral(
                referral_id="referral-2", student_id="lms-student-2", lecturer_id="lecturer-1",
                module_id="lms-module-1", risk_level="LOW", risk_score=0.2,
                reason="Other student", urgency="STANDARD",
            ),
        ])
        db.flush()
        db.add(Intervention(
            intervention_id="intervention-1", referral_id="referral-1",
            student_id="lms-student-1", advisor_user_id="advisor-1",
            strategy="Weekly check-in", reason="Attendance support",
            date_started=datetime(2026, 4, 12, 9, 30),
        ))
        db.add(StudentMeeting(
            meeting_id="meeting-1", referral_id="referral-1",
            student_id="lms-student-1", advisor_user_id="advisor-1",
            meeting_at=datetime(2026, 4, 13, 10, 0), purpose="Discuss progress",
        ))
        db.add_all([
            WorkbookIntelligence(
                record_id="weekly-1", sheet_name="Weekly", row_number=1,
                payload='{"week":"2026-04-12","students":10}',
            ),
            WorkbookIntelligence(
                record_id="other-1", sheet_name="Other", row_number=1,
                payload='{"week":"2026-04-12","students":3}',
            ),
        ])
        db.commit()
    monkeypatch.setattr(csv_data, "LMSSessionLocal", factory)

    referrals = csv_client.get(
        "/api/admin/csv/export/referrals",
        params={"student_id": "lms-student-1", "date_from": "2026-01-01", "columns": "referral_id,reason"},
    )
    assert referrals.status_code == 200
    referral_rows = list(csv.reader(io.StringIO(referrals.content.decode("utf-8-sig"), newline="")))
    assert referral_rows == [
        ["referral_id", "reason"],
        ["referral-1", 'Concern, with "quotes"\nand another line'],
    ]

    interventions = csv_client.get(
        "/api/admin/csv/export/interventions",
        params={"student_id": "lms-student-1", "date_from": "2026-04-12", "date_to": "2026-04-12",
                "columns": "intervention_id,student_id"},
    )
    assert interventions.status_code == 200
    assert list(csv.reader(io.StringIO(interventions.content.decode("utf-8-sig"), newline=""))) == [
        ["intervention_id", "student_id"], ["intervention-1", "lms-student-1"],
    ]

    meetings = csv_client.get(
        "/api/admin/csv/export/meetings",
        params={"student_id": "lms-student-1", "date_from": "2026-04-13", "date_to": "2026-04-13",
                "columns": "meeting_id,student_id"},
    )
    assert meetings.status_code == 200
    assert list(csv.reader(io.StringIO(meetings.content.decode("utf-8-sig"), newline=""))) == [
        ["meeting_id", "student_id"], ["meeting-1", "lms-student-1"],
    ]

    response = csv_client.get("/api/admin/csv/export/workbook-intelligence", params={"sheet_name": "Weekly"})
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"), newline="")))
    assert rows == [
        ["record_id", "sheet_name", "row_number", "payload"],
        ["weekly-1", "Weekly", "1", '{"week":"2026-04-12","students":10}'],
    ]
    assert csv_client.get(
        "/api/admin/csv/export/workbook-intelligence", params={"sheet_name": "Missing"},
    ).status_code == 404
    assert csv_client.get(
        "/api/admin/csv/export/referrals", params={"student_id": "missing"},
    ).status_code == 404
    engine.dispose()
