import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from app.database.connection import Base


class LearningTopic(Base):
    __tablename__ = "learning_topics"
    __table_args__ = (UniqueConstraint("module_id", "name", name="uq_learning_topic_module_name"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    module = relationship("Module")
    feedback = relationship("TopicFeedback", back_populates="topic", cascade="all, delete-orphan")
    resources = relationship("LearningResource", back_populates="topic", cascade="all, delete-orphan")


class TopicFeedback(Base):
    __tablename__ = "topic_feedback"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(ForeignKey("learning_topics.id"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    lecturer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    learning_gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    learning_goal: Mapped[Optional[str]] = mapped_column(Text)
    goal_due_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    topic = relationship("LearningTopic", back_populates="feedback")
    student = relationship("StudentProfile")
    lecturer = relationship("User")


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(ForeignKey("learning_topics.id"), nullable=False, index=True)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_student_id: Mapped[Optional[str]] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, default="link")
    resource_url: Mapped[Optional[str]] = mapped_column(String(2048))
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_data: Mapped[Optional[bytes]] = deferred(mapped_column(LargeBinary))
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="lecturer")
    reviewed_by_lecturer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recommended_reason: Mapped[Optional[str]] = mapped_column(Text)
    display_priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    topic = relationship("LearningTopic", back_populates="resources")
    progress = relationship("LearningProgress", back_populates="resource", cascade="all, delete-orphan")


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (UniqueConstraint("student_id", "resource_id", name="uq_learning_progress_student_resource"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("learning_resources.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="viewed")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resource = relationship("LearningResource", back_populates="progress")


class ClassAttendanceRecord(Base):
    __tablename__ = "class_attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "module_id", "class_name", "class_date", name="uq_class_attendance_student_class"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"), nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(160), nullable=False)
    class_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    module = relationship("Module")
    student = relationship("StudentProfile")


class WellnessReferral(Base):
    __tablename__ = "wellness_referrals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    student_message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    student = relationship("StudentProfile")


class WellnessAppointmentSlot(Base):
    __tablename__ = "wellness_appointment_slots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WellnessAppointment(Base):
    __tablename__ = "wellness_appointments"
    __table_args__ = (
        Index(
            "uq_active_wellness_appointment_slot",
            "slot_id",
            unique=True,
            sqlite_where=text("status IN ('confirmed', 'follow_up')"),
            postgresql_where=text("status IN ('confirmed', 'follow_up')"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    referral_id: Mapped[str] = mapped_column(ForeignKey("wellness_referrals.id"), nullable=False, index=True)
    slot_id: Mapped[str] = mapped_column(ForeignKey("wellness_appointment_slots.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="confirmed")
    booked_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    follow_up: Mapped[Optional[str]] = mapped_column(String(500))
    slot = relationship("WellnessAppointmentSlot")
    referral = relationship("WellnessReferral")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ImportedDatasetState(Base):
    __tablename__ = "imported_dataset_states"

    dataset_id: Mapped[str] = mapped_column(String, primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
