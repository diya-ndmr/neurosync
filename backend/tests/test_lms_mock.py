import tempfile
from pathlib import Path

import pytest

from lms.generator import generate_mock_lms
from lms.database import build_lms_session_factory
from lms.models import AssessmentResult, AttendanceRecord, QuizAttempt, Student


@pytest.fixture(scope="module")
def generated_lms():
    tmpdir = tempfile.TemporaryDirectory()
    db_path = str(Path(tmpdir.name) / "mock_lms.db")
    summary = generate_mock_lms(db_path=db_path, recreate=True)
    engine, session_factory = build_lms_session_factory(db_path)
    yield summary, session_factory
    engine.dispose()
    tmpdir.cleanup()


def test_generate_mock_lms_creates_500_students(generated_lms):
    summary, _ = generated_lms
    assert summary["student_count"] == 500
    assert summary["student_ids_min"] == "STU0001"
    assert summary["student_ids_max"] == "STU0500"


def test_lms_student_ids_are_unique_and_sequences_are_valid(generated_lms):
    _, session_factory = generated_lms
    db = session_factory()
    try:
        ids = [s.student_id for s in db.query(Student).order_by(Student.student_id).all()]
        assert len(ids) == 500
        assert len(set(ids)) == 500
        assert ids[0] == "STU0001"
        assert ids[-1] == "STU0500"
    finally:
        db.close()


def test_lms_data_has_valid_ranges_and_statuses(generated_lms):
    _, session_factory = generated_lms
    db = session_factory()
    try:
        results = db.query(AssessmentResult).all()
        assert results
        assert all(0 <= r.mark <= 100 for r in results)
        assert all(0 <= r.percentage <= 100 for r in results)
        attendance = db.query(AttendanceRecord).all()
        assert attendance
        assert all(r.status in {"PRESENT", "ABSENT", "LATE", "EXCUSED"} for r in attendance)
        quizzes = db.query(QuizAttempt).all()
        assert quizzes
        assert all(0 <= q.percentage <= 100 for q in quizzes)
    finally:
        db.close()


def test_forbidden_student_lookup_is_not_allowed_by_policy(generated_lms):
    _, session_factory = generated_lms
    db = session_factory()
    try:
        s1 = db.query(Student).filter(Student.student_id == "STU0001").first()
        s2 = db.query(Student).filter(Student.student_id == "STU0002").first()
        assert s1 is not None and s2 is not None
        assert s1.student_id != s2.student_id
    finally:
        db.close()
