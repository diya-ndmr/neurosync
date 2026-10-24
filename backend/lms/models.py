import enum
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import LMSBase


class StudentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    LEAVE = "LEAVE"
    SUSPENDED = "SUSPENDED"
    GRADUATED = "GRADUATED"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class AssessmentType(str, enum.Enum):
    ASSIGNMENT = "ASSIGNMENT"
    TEST = "TEST"
    PROJECT = "PROJECT"
    EXAM = "EXAM"


class ResultStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    LATE = "LATE"
    MISSING = "MISSING"
    NOT_YET_DUE = "NOT_YET_DUE"


class ActivityType(str, enum.Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW_MODULE = "VIEW_MODULE"
    VIEW_RESOURCE = "VIEW_RESOURCE"
    DOWNLOAD_RESOURCE = "DOWNLOAD_RESOURCE"
    VIEW_ASSESSMENT = "VIEW_ASSESSMENT"
    QUIZ_ATTEMPT = "QUIZ_ATTEMPT"
    DISCUSSION_VIEW = "DISCUSSION_VIEW"
    DISCUSSION_POST = "DISCUSSION_POST"


class Programme(LMSBase):
    __tablename__ = "programmes"

    programme_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"PRG-{uuid.uuid4().hex[:8].upper()}")
    programme_code = Column(String, unique=True, nullable=False)
    programme_name: Mapped[str] = mapped_column(String, nullable=False)
    faculty = Column(String, nullable=False)
    level = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    students = relationship("Student", back_populates="programme")
    modules = relationship("Module", back_populates="programme")


class Lecturer(LMSBase):
    __tablename__ = "lecturers"

    lecturer_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"LEC-{uuid.uuid4().hex[:8].upper()}")
    first_name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    department = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    modules = relationship("Module", back_populates="lecturer")


class StaffMapping(LMSBase):
    __tablename__ = "staff_mappings"

    app_user_email: Mapped[str] = mapped_column(String, primary_key=True)
    lecturer_id: Mapped[str] = mapped_column(ForeignKey("lecturers.lecturer_id"), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class StudentMapping(LMSBase):
    __tablename__ = "student_mappings"

    app_user_email: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Student(LMSBase):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    surname: Mapped[str] = mapped_column(String, nullable=False)
    institutional_email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    programme_id = Column(String, ForeignKey("programmes.programme_id"), nullable=False)
    year_of_study: Mapped[int] = mapped_column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    behaviour_group: Mapped[str] = mapped_column(String, nullable=False, default="stable")
    enrolment_status: Mapped[str] = mapped_column(String, nullable=False, default=StudentStatus.ACTIVE.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    programme = relationship("Programme", back_populates="students")
    module_enrolments = relationship("ModuleEnrolment", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    assessment_results = relationship("AssessmentResult", back_populates="student", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    lms_activity = relationship("LMSActivity", back_populates="student", cascade="all, delete-orphan")
    resource_activity = relationship("ResourceActivity", back_populates="student", cascade="all, delete-orphan")


class MonthlyAttendanceSummary(LMSBase):
    __tablename__ = "monthly_attendance_summaries"

    summary_id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    month: Mapped[str] = mapped_column(String, nullable=False)
    scheduled_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    attended_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_leave_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    unexcused_absences: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (UniqueConstraint("student_id", "month", name="uq_student_attendance_month"),)


class ApprovedLeaveRecord(LMSBase):
    __tablename__ = "approved_leave_records"

    leave_id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    month: Mapped[str] = mapped_column(String, nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approval_status: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)


class DatasetImport(LMSBase):
    __tablename__ = "dataset_imports"

    import_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    student_count: Mapped[int] = mapped_column(Integer, nullable=False)
    attendance_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    leave_count: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkbookIntelligence(LMSBase):
    __tablename__ = "workbook_intelligence"

    record_id: Mapped[str] = mapped_column(String, primary_key=True)
    sheet_name: Mapped[str] = mapped_column(String, index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)


class DatasetSourceRow(LMSBase):
    __tablename__ = "dataset_source_rows"

    source_row_id: Mapped[str] = mapped_column(String, primary_key=True)
    source_name: Mapped[str] = mapped_column(String, index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)


class Module(LMSBase):
    __tablename__ = "modules"

    module_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"MOD-{uuid.uuid4().hex[:8].upper()}")
    programme_id = Column(String, ForeignKey("programmes.programme_id"), nullable=False)
    module_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    module_name: Mapped[str] = mapped_column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    lecturer_id: Mapped[str] = mapped_column(String, ForeignKey("lecturers.lecturer_id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    programme = relationship("Programme", back_populates="modules")
    lecturer = relationship("Lecturer", back_populates="modules")
    enrolments = relationship("ModuleEnrolment", back_populates="module", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="module", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="module", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="module", cascade="all, delete-orphan")
    lms_activity = relationship("LMSActivity", back_populates="module", cascade="all, delete-orphan")
    resource_activity = relationship("ResourceActivity", back_populates="module", cascade="all, delete-orphan")


class ModuleEnrolment(LMSBase):
    __tablename__ = "module_enrolments"

    enrolment_id = Column(String, primary_key=True, default=lambda: f"ENR-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.module_id"), nullable=False)
    status = Column(String, nullable=False, default="ENROLLED")
    enrolled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("student_id", "module_id", name="uq_student_module_enrolment"),)

    student = relationship("Student", back_populates="module_enrolments")
    module = relationship("Module", back_populates="enrolments")


class AttendanceSession(LMSBase):
    __tablename__ = "attendance_sessions"

    session_id = Column(String, primary_key=True, default=lambda: f"ATS-{uuid.uuid4().hex[:8].upper()}")
    module_id = Column(String, ForeignKey("modules.module_id"), nullable=False)
    session_date = Column(Date, nullable=False)
    session_type: Mapped[str] = mapped_column(String, nullable=False, default="LECTURE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(LMSBase):
    __tablename__ = "attendance_records"

    attendance_id = Column(String, primary_key=True, default=lambda: f"ATT-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.module_id"), nullable=False)
    session_id = Column(String, ForeignKey("attendance_sessions.session_id"), nullable=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="attendance_records")
    module = relationship("Module", back_populates="attendance_records")
    session = relationship("AttendanceSession", back_populates="records")


class Assessment(LMSBase):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"ASM-{uuid.uuid4().hex[:8].upper()}")
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.module_id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    assessment_type: Mapped[str] = mapped_column(String, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_mark = Column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    module = relationship("Module", back_populates="assessments")
    results = relationship("AssessmentResult", back_populates="assessment", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentResult(LMSBase):
    __tablename__ = "assessment_results"

    result_id = Column(String, primary_key=True, default=lambda: f"RES-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String, ForeignKey("assessments.assessment_id"), nullable=False)
    mark: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    submission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="assessment_results")
    assessment = relationship("Assessment", back_populates="results")


class Quiz(LMSBase):
    __tablename__ = "quizzes"

    quiz_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"QZ-{uuid.uuid4().hex[:8].upper()}")
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.module_id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    available_date: Mapped[date] = mapped_column(Date, nullable=False)
    maximum_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    module = relationship("Module", back_populates="quizzes")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizAttempt(LMSBase):
    __tablename__ = "quiz_attempts"

    attempt_id = Column(String, primary_key=True, default=lambda: f"QAT-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    quiz_id: Mapped[str] = mapped_column(String, ForeignKey("quizzes.quiz_id"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="attempts")


class Submission(LMSBase):
    __tablename__ = "submissions"

    submission_id = Column(String, primary_key=True, default=lambda: f"SUB-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String, ForeignKey("assessments.assessment_id"), nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="SUBMITTED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="submissions")
    assessment = relationship("Assessment", back_populates="submissions")


class LMSActivity(LMSBase):
    __tablename__ = "lms_activity"

    activity_id = Column(String, primary_key=True, default=lambda: f"ACT-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    module_id = Column(String, ForeignKey("modules.module_id"), nullable=True)
    session_duration = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="lms_activity")
    module = relationship("Module", back_populates="lms_activity")


class ResourceActivity(LMSBase):
    __tablename__ = "resource_activity"

    resource_activity_id = Column(String, primary_key=True, default=lambda: f"RSC-{uuid.uuid4().hex[:8].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    module_id = Column(String, ForeignKey("modules.module_id"), nullable=True)
    resource_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="resource_activity")
    module = relationship("Module", back_populates="resource_activity")


class Referral(LMSBase):
    __tablename__ = "student_referrals"

    referral_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"REF-{uuid.uuid4().hex[:10].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    lecturer_id: Mapped[str] = mapped_column(String, ForeignKey("lecturers.lecturer_id"), nullable=False)
    advisor_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    module_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("modules.module_id"), nullable=True)
    risk_assessment_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    lecturer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String, nullable=False, default="STANDARD")
    status: Mapped[str] = mapped_column(String, nullable=False, default="REFERRED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Intervention(LMSBase):
    __tablename__ = "student_interventions"

    intervention_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"INT-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    advisor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    advisor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_started: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PLANNED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AcademicSnapshot(LMSBase):
    """Immutable copy of a student's academic indicators at a point in the case.

    Snapshots let the follow-up stage compare academic indicators recorded before
    an intervention with the current position, without rewriting evidence.
    """

    __tablename__ = "academic_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"SNAP-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    captured_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    label: Mapped[str] = mapped_column(String, nullable=False, default="BEFORE_INTERVENTION", index=True)
    attendance: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attendance_30d: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    academic_average: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    submission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    missing_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quiz_average: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class MockEmail(LMSBase):
    __tablename__ = "mock_emails"

    message_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"MSG-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    advisor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    drafted_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String, nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class StudentMeeting(LMSBase):
    __tablename__ = "student_meetings"

    meeting_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"MTG-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    advisor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    meeting_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="MEETING_SCHEDULED")
    advisor_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class StudentResponse(LMSBase):
    __tablename__ = "synthetic_student_responses"

    response_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"RSP-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    message_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("mock_emails.message_id"), nullable=True)
    response_type: Mapped[str] = mapped_column(String, nullable=False)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class AdvisorNote(LMSBase):
    __tablename__ = "advisor_only_notes"

    note_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"NOTE-{uuid.uuid4().hex[:10].upper()}")
    referral_id: Mapped[str] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    advisor_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class WorkflowEvent(LMSBase):
    __tablename__ = "student_workflow_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: f"EVT-{uuid.uuid4().hex[:10].upper()}")
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.student_id"), nullable=False, index=True)
    referral_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("student_referrals.referral_id"), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    visibility: Mapped[str] = mapped_column(String, nullable=False, default="SHARED")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


__all__ = [
    "StudentStatus",
    "AttendanceStatus",
    "AssessmentType",
    "ResultStatus",
    "ActivityType",
    "Programme",
    "Lecturer",
    "StaffMapping",
    "StudentMapping",
    "Student",
    "MonthlyAttendanceSummary",
    "ApprovedLeaveRecord",
    "DatasetImport",
    "DatasetSourceRow",
    "Module",
    "ModuleEnrolment",
    "AttendanceSession",
    "AttendanceRecord",
    "Assessment",
    "AssessmentResult",
    "Quiz",
    "QuizAttempt",
    "Submission",
    "LMSActivity",
    "ResourceActivity",
    "Referral",
    "Intervention",
    "AcademicSnapshot",
    "MockEmail",
    "StudentMeeting",
    "StudentResponse",
    "AdvisorNote",
    "WorkflowEvent",
]
