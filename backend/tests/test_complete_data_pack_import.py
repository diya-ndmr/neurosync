from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models import Attendance, ClassAttendanceRecord, LearningResource, StudentProfile, UserPreference
from app.models.learning_support import ImportedDatasetState
from app.models.user import User, UserRole
from lms.complete_data_pack_import import (
    DATASET_ID,
    DEFAULT_BUNDLE,
    _source_identifier,
    import_complete_data_pack,
)
from lms.database import build_lms_session_factory
from lms.models import AttendanceRecord, DatasetImport, DatasetSourceRow, Student


def test_source_row_identifiers_preserve_composite_keys_and_sensitive_fields():
    assert _source_identifier(
        "student_module_enrolments.csv",
        {"student_id": "STU0001", "module_id": "MOD001", "enrolment_status": "Active"},
        2,
    ) == "STU0001:MOD001"
    assert _source_identifier(
        "advisor_assignments.csv",
        {"student_id": "STU0001", "advisor_id": "ADV001"},
        2,
    ) == "STU0001:ADV001"
    assert _source_identifier(
        "master_student_snapshot.csv",
        {"student_id": "STU0001", "advisor_id": "ADV001"},
        2,
    ) == "STU0001"


def test_complete_data_pack_import_is_sanitized_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr("lms.complete_data_pack_import.hash_password", lambda password: f"test:{password}")
    app_engine = create_engine(
        f"sqlite:///{tmp_path / 'app.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(app_engine)
    app_factory = sessionmaker(bind=app_engine, autoflush=False, autocommit=False)
    app_db = app_factory()
    legacy_hash = "retained-demo-password-hash"
    try:
        legacy_students = [
            User(
                id=f"legacy-student-{index}",
                email=f"legacy-{index}@example.edu",
                name=f"Legacy Student {index}",
                password_hash=legacy_hash,
                role=UserRole.student,
            )
            for index in range(1, 7)
        ]
        app_db.add_all(legacy_students)
        app_db.add_all([
            User(
                id="legacy-lecturer",
                email="legacy-lecturer@example.edu",
                name="Legacy Lecturer",
                password_hash=legacy_hash,
                role=UserRole.lecturer,
            ),
            User(
                id="legacy-advisor",
                email="legacy-advisor@example.edu",
                name="Legacy Advisor",
                password_hash=legacy_hash,
                role=UserRole.advisor,
            ),
            User(
                id="legacy-admin",
                email="legacy-admin@example.edu",
                name="Legacy Admin",
                password_hash=legacy_hash,
                role=UserRole.admin,
            ),
        ])
        app_db.flush()
        app_db.add_all([
            StudentProfile(
                id=f"legacy-profile-{index}",
                user_id=f"legacy-student-{index}",
                student_number=f"OLD{index:04}",
                first_name="Legacy",
                surname=f"Student {index}",
                programme="Legacy Programme",
            )
            for index in range(1, 7)
        ])
        app_db.commit()
    finally:
        app_db.close()

    lms_url = f"sqlite:///{tmp_path / 'lms.db'}"
    try:
        first = import_complete_data_pack(
            DEFAULT_BUNDLE,
            lms_url,
            replace=True,
            app_database_engine=app_engine,
            app_session_factory=app_factory,
        )
        assert first["status"] == "imported"
        app_db = app_factory()
        try:
            assert app_db.query(StudentProfile).count() == 500
            assert app_db.query(ClassAttendanceRecord).count() == 110112
            assert app_db.query(ClassAttendanceRecord).filter_by(status="approved_leave").count() == 1559
            assert app_db.query(Attendance).count() == 108553
            assert app_db.query(LearningResource).count() == 883
            assert app_db.query(LearningResource).filter_by(reviewed_by_lecturer=False).count() == 427
            first_preference = app_db.query(UserPreference).filter_by(user_id="legacy-student-1").one()
            assert first_preference.settings["preferred_study_start"] == "20:00"
            assert first_preference.settings["timezone"] == "Africa/Johannesburg"
            retained_user = app_db.query(User).filter_by(id="legacy-student-1").one()
            assert retained_user.email == "sanele.mthethwa1@students.neurosync.example"
            assert retained_user.password_hash == legacy_hash
            assert app_db.query(ImportedDatasetState).filter_by(dataset_id=DATASET_ID).count() == 1
        finally:
            app_db.close()

        engine, lms_factory = build_lms_session_factory(database_url=lms_url)
        lms_db = lms_factory()
        try:
            assert lms_db.query(Student).count() == 500
            assert lms_db.query(AttendanceRecord).count() == 110112
            assert lms_db.query(DatasetImport).count() == 1
            assert lms_db.query(DatasetSourceRow).filter(
                DatasetSourceRow.payload.contains("password_hash_demo")
            ).count() == 0
            assert lms_db.query(DatasetSourceRow).filter(
                DatasetSourceRow.payload.contains("confidentiality_note")
            ).count() == 0
            enrolments = lms_db.query(DatasetSourceRow).filter_by(
                source_name="student_module_enrolments.csv"
            )
            assert enrolments.count() == 2000
            assert enrolments.filter_by(source_row_id="complete-pack:student_module_enrolments.csv:STU0001:MOD001").count() == 1
        finally:
            lms_db.close()
            engine.dispose()

        repeated = import_complete_data_pack(
            DEFAULT_BUNDLE,
            lms_url,
            replace=True,
            app_database_engine=app_engine,
            app_session_factory=app_factory,
        )
        assert repeated["status"] == "already_imported"
    finally:
        app_engine.dispose()
