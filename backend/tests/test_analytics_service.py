from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.models.risk_prediction import RiskLevel, RiskPrediction
from app.models.student import StudentProfile
from app.models.user import User, UserRole
from app.services.analytics_service import get_admin_analytics


def _analytics_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'analytics.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def test_admin_analytics_reports_empty_source_data_without_fabricated_values(tmp_path):
    engine, db = _analytics_session(tmp_path)
    try:
        result = get_admin_analytics(db)
    finally:
        db.close()
        engine.dispose()

    assert result["total_students"] == 0
    assert result["active_students"] is None
    assert result["average_performance"] is None
    assert result["retention_rate"] is None
    assert result["high_risk_students"] == 0
    assert result["risk_distribution"] == [
        {"name": "LOW", "value": 0},
        {"name": "MEDIUM", "value": 0},
        {"name": "HIGH", "value": 0},
    ]
    assert result["attendance_trend"] == []
    assert result["performance_trend"] == []
    assert result["programme_comparison"] == []


def test_risk_distribution_uses_only_each_students_latest_prediction(tmp_path):
    engine, db = _analytics_session(tmp_path)
    now = datetime.now(timezone.utc)
    try:
        users = [
            User(id="user-1", email="one@example.edu", password_hash="x", name="One", role=UserRole.student),
            User(id="user-2", email="two@example.edu", password_hash="x", name="Two", role=UserRole.student),
        ]
        students = [
            StudentProfile(id="student-1", user_id="user-1", student_number="A1", first_name="One", surname="Student", programme="Computing", year_level=1),
            StudentProfile(id="student-2", user_id="user-2", student_number="A2", first_name="Two", surname="Student", programme="Computing", year_level=1),
        ]
        predictions = [
            RiskPrediction(id="old-high", student_id="student-1", risk_score=90, risk_level=RiskLevel.HIGH, explanation="Earlier", model_version="v1", created_at=now - timedelta(days=1)),
            RiskPrediction(id="current-low", student_id="student-1", risk_score=20, risk_level=RiskLevel.LOW, explanation="Latest", model_version="v2", created_at=now),
            RiskPrediction(id="current-medium", student_id="student-2", risk_score=55, risk_level=RiskLevel.MEDIUM, explanation="Latest", model_version="v1", created_at=now),
        ]
        db.add_all(users + students + predictions)
        db.commit()
        result = get_admin_analytics(db)
    finally:
        db.close()
        engine.dispose()

    assert result["risk_distribution"] == [
        {"name": "LOW", "value": 1},
        {"name": "MEDIUM", "value": 1},
        {"name": "HIGH", "value": 0},
    ]
    assert result["high_risk_students"] == 0
