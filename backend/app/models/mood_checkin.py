import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class MoodCheckin(Base):
    __tablename__ = "mood_checkins"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), nullable=False)
    mood_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    stress_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-10
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships
    student = relationship("StudentProfile", back_populates="mood_checkins")
