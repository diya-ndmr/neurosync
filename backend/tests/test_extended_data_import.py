import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
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
from app.models.user import UserRole
from lms.extended_data_import import DEFAULT_BUNDLE, import_extended_data_pack


@pytest.fixture
def app_db(tmp_path, monkeypatch):
    monkeypatch.setattr("lms.extended_data_import.hash_password", lambda password: f"test:{password}")
    engine = create_engine(f"sqlite:///{tmp_path / 'extended.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_extended_bundle_import_is_namespaced_and_idempotent(app_db):
    existing_user = User(
        id="existing-student-user",
        email="sanele.mthethwa1@students.neurosync.example",
        password_hash="existing-hash",
        name="Sanele Mthethwa",
        role=UserRole.student,
    )
    app_db.add(existing_user)
    app_db.flush()
    app_db.add(
        StudentProfile(
            id="STU0001",
            user_id=existing_user.id,
            student_number="STU0001",
            first_name="Sanele",
            surname="Mthethwa",
            programme="Existing programme",
            year_level=2,
        )
    )
    app_db.commit()

    first = import_extended_data_pack(app_db, DEFAULT_BUNDLE, "demo1234")
    second = import_extended_data_pack(app_db, DEFAULT_BUNDLE, "demo1234")

    assert first == {
        "students": 50,
        "assessment_feedback": 50,
        "quiz_question_results": 250,
        "risk_predictions": 50,
        "mood_checkins": 150,
        "study_sessions": 150,
        "recommendations": 20,
    }
    assert second == first
    assert app_db.query(StudentProfile).filter(StudentProfile.id == "STU0001").one().first_name == "Sanele"
    assert app_db.query(StudentProfile).filter(StudentProfile.id == "EXT-STU0001").one().first_name == "Venisha"
    assert app_db.query(User).filter(User.id == "EXT-USER-STU0001").one().password_hash == "test:demo1234"
    assert app_db.query(ExtendedAssessmentFeedback).count() == 50
    assert app_db.query(ExtendedQuizQuestionResult).count() == 250
    assert app_db.query(RiskPrediction).count() == 50
    assert app_db.query(MoodCheckin).count() == 150
    assert app_db.query(StudySession).count() == 150
    assert app_db.query(Recommendation).count() == 20
    risk = app_db.query(RiskPrediction).filter(RiskPrediction.student_id == "EXT-STU0001").one()
    assert risk.risk_score == 34
    assert "Missed Wellness Appointments" in risk.explanation


def test_extended_bundle_refuses_existing_email_collision(app_db):
    app_db.add(
        User(
            id="unrelated-user",
            email="venisha.zuma+ext-stu0001@neurosync.edu",
            password_hash="existing-hash",
            name="Different account",
            role=UserRole.student,
        )
    )
    app_db.commit()

    with pytest.raises(ValueError, match="already exists"):
        import_extended_data_pack(app_db, DEFAULT_BUNDLE, "demo1234")

    assert app_db.query(StudentProfile).count() == 0
    assert app_db.query(RiskPrediction).count() == 0
