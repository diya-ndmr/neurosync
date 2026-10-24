from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.middleware.security import get_current_user
from app.models.user import UserRole
from app.api import mock_lms as mock_lms_api
from app.api import workflow as workflow_api
from lms.database import LMSBase
from lms.models import (
    Assessment,
    AssessmentResult,
    AttendanceRecord,
    AttendanceSession,
    Intervention,
    Lecturer,
    Module,
    ModuleEnrolment,
    Programme,
    Quiz,
    QuizAttempt,
    StaffMapping,
    Student,
    Submission,
)


@pytest.fixture
def workflow_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'workflow.db'}", connect_args={"check_same_thread": False})
    LMSBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    programme = Programme(programme_id="PRG-TEST", programme_code="TEST", programme_name="Test Programme", faculty="Test", level="Undergraduate")
    lecturer = Lecturer(lecturer_id="LEC001", first_name="Demo", surname="Lecturer", email="lecturer@university.edu", department="Computing")
    module = Module(module_id="MOD0001", programme_id="PRG-TEST", module_code="TST101", module_name="Test Module", credits=20, semester=1, lecturer_id="LEC001")
    taught_student = Student(student_id="STU0001", first_name="Avery", surname="Example", institutional_email="stu0001@student.neurosync.demo", programme_id="PRG-TEST", year_of_study=1, semester=1, behaviour_group="declining")
    other_student = Student(student_id="STU0002", first_name="Jordan", surname="Example", institutional_email="stu0002@student.neurosync.demo", programme_id="PRG-TEST", year_of_study=1, semester=1, behaviour_group="stable")
    db.add_all([programme, lecturer, module, taught_student, other_student])
    db.flush()
    db.add_all([
        StaffMapping(app_user_email="lecturer@university.edu", lecturer_id="LEC001"),
        ModuleEnrolment(student_id="STU0001", module_id="MOD0001", status="ENROLLED"),
    ])
    due_date = date.today() - timedelta(days=7)
    assessment = Assessment(assessment_id="ASM0001", module_id="MOD0001", title="Assignment 1", assessment_type="ASSIGNMENT", weight=25, maximum_mark=100, due_date=due_date)
    db.add(assessment)
    db.flush()
    db.add_all([
        AssessmentResult(student_id="STU0001", assessment_id="ASM0001", mark=42, percentage=42, submission_date=None, status="MISSING"),
        Submission(student_id="STU0001", assessment_id="ASM0001", submitted_at=None, status="MISSING"),
    ])
    meeting_day = date.today() - timedelta(days=2)
    session = AttendanceSession(module_id="MOD0001", session_date=meeting_day, session_type="LECTURE")
    db.add(session)
    db.flush()
    db.add(AttendanceRecord(student_id="STU0001", module_id="MOD0001", session_id=session.session_id, session_date=meeting_day, status="ABSENT"))
    quiz = Quiz(quiz_id="QZ000001", module_id="MOD0001", title="Quiz 1", available_date=meeting_day, maximum_score=100)
    db.add(quiz)
    db.flush()
    db.add(QuizAttempt(student_id="STU0001", quiz_id="QZ000001", attempt_number=1, score=45, percentage=45, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc), duration=20))
    db.commit()
    db.close()

    monkeypatch.setattr(workflow_api, "LMSSessionLocal", factory)
    monkeypatch.setattr(mock_lms_api, "LMSSessionLocal", factory)
    identity = {"user": SimpleNamespace(id="lecturer-user", email="lecturer@university.edu", role=UserRole.lecturer)}
    app = FastAPI()
    app.include_router(workflow_api.router)
    app.include_router(mock_lms_api.router)
    app.dependency_overrides[get_current_user] = lambda: identity["user"]
    client = TestClient(app)
    yield client, identity
    client.close()
    engine.dispose()


def _refer(client: TestClient):
    return client.post("/api/workflow/referrals", json={
        "student_id": "STU0001",
        "module_id": "MOD0001",
        "reason": "Attendance and assessment indicators have declined.",
        "lecturer_notes": "Please review academic support options.",
        "urgency": "STANDARD",
    })


def test_lecturer_student_scope_and_lms_records(workflow_client):
    client, _ = workflow_client
    roster = client.get("/api/workflow/lecturer/students")
    assert roster.status_code == 200
    assert [item["student_id"] for item in roster.json()["items"]] == ["STU0001"]

    review = client.get("/api/workflow/students/STU0001/review")
    assert review.status_code == 200
    payload = review.json()
    assert payload["student"]["institutional_email"] == "stu0001@student.neurosync.demo"
    assert payload["metrics"]["missing_submissions"] == 1
    assert payload["attendance"][0]["status"] == "ABSENT"
    assert payload["risk"]["evidence"]
    assert payload["risk"]["trajectory"] in {
        "improving", "stable", "slowly_deteriorating", "rapidly_deteriorating"
    }

    forbidden = client.get("/api/workflow/students/STU0002/review")
    assert forbidden.status_code == 404
    old_lms_route = client.get("/api/lms/students/STU0002/attendance")
    assert old_lms_route.status_code == 404


def test_module_assessment_intelligence_reports_evidence_and_enforces_scope(workflow_client):
    client, _ = workflow_client
    db = workflow_api.LMSSessionLocal()
    try:
        db.add(Student(
            student_id="STU0003", first_name="Casey", surname="Example",
            institutional_email="stu0003@student.neurosync.demo", programme_id="PRG-TEST",
            year_of_study=1, semester=1, behaviour_group="stable",
        ))
        db.add_all([
            ModuleEnrolment(student_id="STU0002", module_id="MOD0001", status="ENROLLED"),
            ModuleEnrolment(student_id="STU0003", module_id="MOD0001", status="ENROLLED"),
        ])
        previous = Assessment(
            assessment_id="ASM0002", module_id="MOD0001", title="Assessment 2",
            assessment_type="TEST", weight=25, maximum_mark=100, due_date=date.today() - timedelta(days=14),
        )
        current = Assessment(
            assessment_id="ASM0003", module_id="MOD0001", title="Assessment 3",
            assessment_type="TEST", weight=25, maximum_mark=100, due_date=date.today() - timedelta(days=7),
        )
        db.add_all([previous, current])
        db.flush()
        for student_id, previous_mark, current_mark in (
            ("STU0001", 80, 55), ("STU0002", 82, 56), ("STU0003", 78, 54),
        ):
            db.add_all([
                AssessmentResult(student_id=student_id, assessment_id="ASM0002", mark=previous_mark, percentage=previous_mark, status="SUBMITTED"),
                AssessmentResult(student_id=student_id, assessment_id="ASM0003", mark=current_mark, percentage=current_mark, status="SUBMITTED"),
            ])
        db.commit()
    finally:
        db.close()

    response = client.get("/api/workflow/lecturer/modules/MOD0001/assessment-intelligence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ANOMALY_DETECTED"
    assert payload["comparison"]["current_student_count"] == 3
    assert payload["comparison"]["change_percentage_points"] == -25.0
    assert "does not establish a cause" in payload["interpretation"]
    assert client.get("/api/workflow/lecturer/modules/MOD9999/assessment-intelligence").status_code == 404


def test_module_assessment_intelligence_requires_two_assessments_and_minimum_cohort(workflow_client):
    client, _ = workflow_client
    single_assessment = client.get("/api/workflow/lecturer/modules/MOD0001/assessment-intelligence")
    assert single_assessment.status_code == 200
    assert single_assessment.json()["status"] == "INSUFFICIENT_DATA"

    db = workflow_api.LMSSessionLocal()
    try:
        previous = Assessment(
            assessment_id="ASM0002", module_id="MOD0001", title="Assessment 2",
            assessment_type="TEST", weight=25, maximum_mark=100, due_date=date.today() - timedelta(days=14),
        )
        current = Assessment(
            assessment_id="ASM0003", module_id="MOD0001", title="Assessment 3",
            assessment_type="TEST", weight=25, maximum_mark=100, due_date=date.today() - timedelta(days=7),
        )
        db.add_all([previous, current])
        db.flush()
        db.add_all([
            AssessmentResult(student_id="STU0001", assessment_id="ASM0002", mark=80, percentage=80, status="SUBMITTED"),
            AssessmentResult(student_id="STU0001", assessment_id="ASM0003", mark=65, percentage=65, status="SUBMITTED"),
        ])
        db.commit()
    finally:
        db.close()

    small_cohort = client.get("/api/workflow/lecturer/modules/MOD0001/assessment-intelligence")
    assert small_cohort.status_code == 200
    assert small_cohort.json()["status"] == "INSUFFICIENT_COHORT"


def test_weekly_briefing_is_role_scoped_and_management_receives_aggregates_only(workflow_client):
    client, identity = workflow_client
    created = _refer(client)
    assert created.status_code == 201
    referral_id = created.json()["referral_id"]
    db = workflow_api.LMSSessionLocal()
    try:
        db.add_all([
            Intervention(
                intervention_id="INT-OWNED", referral_id=referral_id, student_id="STU0001",
                advisor_user_id="advisor-user", strategy="Academic Planning Session", reason="Recorded support plan.",
                follow_up_date=date.today() + timedelta(days=3), status="FOLLOW_UP",
            ),
            Intervention(
                intervention_id="INT-OTHER", referral_id=referral_id, student_id="STU0001",
                advisor_user_id="another-advisor", strategy="Attendance Support", reason="Other advisor plan.",
                follow_up_date=date.today() + timedelta(days=2), status="FOLLOW_UP",
            ),
        ])
        db.commit()
    finally:
        db.close()

    lecturer_briefing = client.get("/api/workflow/weekly-briefing")
    assert lecturer_briefing.status_code == 200
    lecturer_payload = lecturer_briefing.json()
    assert lecturer_payload["role"] == "lecturer"
    assert lecturer_payload["summary"]["new_referrals"] == 1
    assert lecturer_payload["items"][0]["referral_id"] == referral_id
    assert lecturer_payload["items"][0]["student_id"] == "STU0001"

    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    advisor_briefing = client.get("/api/workflow/weekly-briefing").json()
    assert advisor_briefing["role"] == "advisor"
    assert advisor_briefing["summary"]["new_referrals"] == 1
    assert advisor_briefing["summary"]["follow_ups_due"] == 1
    follow_up_items = [item for item in advisor_briefing["items"] if item["type"] == "FOLLOW_UP_DUE"]
    assert [item["strategy"] for item in follow_up_items] == ["Academic Planning Session"]

    identity["user"] = SimpleNamespace(id="admin-user", email="admin@university.edu", role=UserRole.admin)
    management_briefing = client.get("/api/workflow/weekly-briefing").json()
    assert management_briefing["role"] == "admin"
    assert management_briefing["summary"]["new_referrals"] == 1
    assert management_briefing["items"] == []
    assert all("student_id" not in item for item in management_briefing["items"])


def test_referral_advisor_assignment_and_confidential_notes(workflow_client):
    client, identity = workflow_client
    created = _refer(client)
    assert created.status_code == 201
    referral_id = created.json()["referral_id"]

    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    queue = client.get("/api/workflow/advisor/dashboard")
    assert queue.status_code == 200
    assert queue.json()["summary"]["new_referrals"] == 1

    detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}")
    assert detail.status_code == 200
    assert detail.json()["review"]["student"]["student_id"] == "STU0001"
    assert detail.json()["recommendations"]

    note = client.post(f"/api/workflow/advisor/referrals/{referral_id}/notes", json={"note": "Private advisor-only follow-up context."})
    assert note.status_code == 201
    advisor_detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}").json()
    assert advisor_detail["advisor_notes"][0]["note"] == "Private advisor-only follow-up context."

    identity["user"] = SimpleNamespace(id="lecturer-user", email="lecturer@university.edu", role=UserRole.lecturer)
    lecturer_detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}")
    assert lecturer_detail.status_code == 200
    assert "advisor_notes" not in lecturer_detail.json()


def test_advisor_can_reject_recommendation_and_create_custom_strategy(workflow_client):
    client, identity = workflow_client
    referral_id = _refer(client).json()["referral_id"]
    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    suggestions = client.get(f"/api/workflow/advisor/referrals/{referral_id}/strategies")
    assert suggestions.status_code == 200

    rejected = client.post(f"/api/workflow/advisor/referrals/{referral_id}/strategies/decision", json={
        "strategy": "Attendance Support", "decision": "DISMISS", "reason": "A different approach is more suitable."
    })
    assert rejected.status_code == 200
    detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}").json()
    assert detail["interventions"] == []

    custom = client.post(f"/api/workflow/advisor/referrals/{referral_id}/strategies/custom", json={
        "strategy": "Weekly planning check-in", "reason": "Build a manageable assessment plan.", "follow_up_date": date.today().isoformat()
    })
    assert custom.status_code == 201
    assert custom.json()["strategy"] == "Weekly planning check-in"


def test_intervention_updates_append_descriptive_shared_history_without_notes(workflow_client):
    client, identity = workflow_client
    referral_id = _refer(client).json()["referral_id"]
    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    created = client.post(f"/api/workflow/advisor/referrals/{referral_id}/strategies/custom", json={
        "strategy": "Weekly planning check-in",
        "reason": "Support an achievable study routine.",
    })
    assert created.status_code == 201
    intervention_id = created.json()["intervention_id"]

    updated = client.patch(f"/api/workflow/advisor/interventions/{intervention_id}", json={
        "status": "FOLLOW_UP",
        "follow_up_date": (date.today() + timedelta(days=7)).isoformat(),
        "advisor_notes": "Private notes must not appear in the shared timeline.",
    })
    assert updated.status_code == 200
    assert updated.json()["intervention_id"] == intervention_id
    assert updated.json()["status"] == "FOLLOW_UP"

    identity["user"] = SimpleNamespace(id="lecturer-user", email="lecturer@university.edu", role=UserRole.lecturer)
    review = client.get("/api/workflow/students/STU0001/review")
    assert review.status_code == 200
    timeline_entry = next(event for event in review.json()["timeline"] if event["event_type"] == "FOLLOW_UP_RECORDED")
    assert "status: PLANNED -> FOLLOW_UP" in timeline_entry["summary"]
    assert "follow-up date:" in timeline_entry["summary"]
    assert "advisor notes updated" in timeline_entry["summary"]
    assert "Private notes" not in timeline_entry["summary"]


def test_mock_email_requires_human_approval_and_meetings_persist(workflow_client):
    client, identity = workflow_client
    referral_id = _refer(client).json()["referral_id"]
    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    draft = client.post(f"/api/workflow/advisor/referrals/{referral_id}/email-drafts", json={
        "subject": "Academic support check-in",
        "body": "We would like to check in about academic support that may be helpful.",
        "drafted_by_ai": False,
    })
    assert draft.status_code == 201
    assert draft.json()["delivery_status"] == "DRAFT"
    assert draft.json()["approval_required"] is True

    sent = client.post(f"/api/workflow/advisor/emails/{draft.json()['message_id']}/approval", json={"approve": True})
    assert sent.status_code == 200
    assert sent.json()["delivery_status"] == "SENT"
    assert sent.json()["external_delivery"] is False

    meeting = client.post(f"/api/workflow/advisor/referrals/{referral_id}/meetings", json={
        "meeting_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "purpose": "Academic support check-in"
    })
    assert meeting.status_code == 201
    assert meeting.json()["status"] == "MEETING_SCHEDULED"

    suggestion = client.get(f"/api/workflow/advisor/referrals/{referral_id}/email-suggestion")
    assert suggestion.status_code == 200
    assert suggestion.json()["requires_advisor_review"] is True
    assert "personal circumstances" in suggestion.json()["body"]

    response = client.post(
        f"/api/workflow/advisor/referrals/{referral_id}/mock-response",
        params={"status_value": "REPLIED", "response": "Synthetic response asking for a meeting."},
    )
    assert response.status_code == 200
    assert response.json()["synthetic"] is True
    advisor_history = client.get(f"/api/workflow/advisor/referrals/{referral_id}").json()["communications"]
    assert any(item["body"] == "Synthetic response asking for a meeting." for item in advisor_history)

    identity["user"] = SimpleNamespace(id="lecturer-user", email="lecturer@university.edu", role=UserRole.lecturer)
    lecturer_history = client.get(f"/api/workflow/advisor/referrals/{referral_id}").json()
    assert "communications" not in lecturer_history
    assert all("Synthetic response asking" not in item["summary"] for item in lecturer_history["timeline"])


def test_academic_baseline_is_captured_once_and_compared(workflow_client):
    client, identity = workflow_client
    referral_id = _refer(client).json()["referral_id"]

    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}")
    assert detail.status_code == 200
    baseline = detail.json()["comparison"]
    assert baseline["has_recorded_intervention"] is False
    assert baseline["caveat"] == "Correlation is not causation."
    assert "no intervention has been recorded yet" in baseline["summary"]
    metrics = {change["metric"] for change in baseline["changes"]}
    assert {"attendance", "academic_average", "submission_rate", "engagement_score"} <= metrics
    assert all(change["before"] == change["current"] for change in baseline["changes"])

    accepted = client.post(f"/api/workflow/advisor/referrals/{referral_id}/strategies/decision", json={
        "strategy": "Attendance Support", "decision": "ACCEPT", "reason": "Address the recorded absences."
    })
    assert accepted.status_code == 200

    comparison = client.get(f"/api/workflow/advisor/referrals/{referral_id}/comparison")
    assert comparison.status_code == 200
    payload = comparison.json()
    assert payload["has_recorded_intervention"] is True
    assert payload["intervention_count"] == 1
    assert payload["summary"].startswith("Academic indicators")
    assert payload["caveat"] == "Correlation is not causation."
    assert all(change["direction"] in {"IMPROVED", "DECLINED", "UNCHANGED"} for change in payload["changes"])

    # The baseline snapshot is immutable evidence, not a moving average.
    repeat = client.get(f"/api/workflow/advisor/referrals/{referral_id}/comparison").json()
    assert repeat["baseline_captured_at"] == payload["baseline_captured_at"]
    assert [change["before"] for change in repeat["changes"]] == [change["before"] for change in payload["changes"]]

    # Lecturers receive the shared comparison but never advisor-only case notes.
    identity["user"] = SimpleNamespace(id="lecturer-user", email="lecturer@university.edu", role=UserRole.lecturer)
    lecturer_review = client.get("/api/workflow/students/STU0001/review")
    assert lecturer_review.status_code == 200
    shared = lecturer_review.json()["intervention_comparison"]
    assert shared["referral_id"] == referral_id
    assert shared["caveat"] == "Correlation is not causation."
    assert "advisor_notes" not in lecturer_review.json()

    lecturer_detail = client.get(f"/api/workflow/advisor/referrals/{referral_id}")
    assert lecturer_detail.status_code == 200
    assert lecturer_detail.json()["comparison"]["direction"] in {"IMPROVED", "DECLINED", "UNCHANGED", "MIXED"}


def test_comparison_requires_an_existing_referral(workflow_client):
    client, identity = workflow_client
    identity["user"] = SimpleNamespace(id="advisor-user", email="advisor@university.edu", role=UserRole.advisor)
    missing = client.get("/api/workflow/advisor/referrals/REF-DOES-NOT-EXIST/comparison")
    assert missing.status_code == 404


def test_referral_payload_rejects_sql_injection_text_in_identifier(workflow_client):
    client, _ = workflow_client
    response = client.post("/api/workflow/referrals", json={
        "student_id": "STU0001' OR 1=1 --", "module_id": "MOD0001", "reason": "Review this student record"
    })
    assert response.status_code == 422
