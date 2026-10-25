import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.connection import Base


class ExtendedAssessmentFeedback(Base):
    __tablename__ = "extended_assessment_feedback"
    __table_args__ = (
        UniqueConstraint("student_id", "external_assessment_id", name="uq_extended_feedback_student_assessment"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), nullable=False, index=True)
    external_assessment_id: Mapped[str] = mapped_column(String, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)


class ExtendedQuizQuestionResult(Base):
    __tablename__ = "extended_quiz_question_results"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "external_assessment_id",
            "question_id",
            name="uq_extended_question_student_assessment_question",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), nullable=False, index=True)
    external_assessment_id: Mapped[str] = mapped_column(String, nullable=False)
    question_id: Mapped[str] = mapped_column(String, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
