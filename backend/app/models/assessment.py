import uuid
from datetime import date, datetime, timezone
from sqlalchemy import String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), nullable=False)
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.id"), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String, nullable=False)  # Exam, Coursework, Quiz, Practical
    mark: Mapped[float] = mapped_column(Float, nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    max_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    topic_name: Mapped[str | None] = mapped_column(String, nullable=True)
    # relationships
    student = relationship("StudentProfile", back_populates="assessments")
    module = relationship("Module", back_populates="assessments")
