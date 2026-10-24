import uuid
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.connection import Base


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    module_code: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String, nullable=False)
    faculty: Mapped[str] = mapped_column(String, nullable=False, default="Computing")

    # relationships
    assessments = relationship("Assessment", back_populates="module")
    attendance_records = relationship("Attendance", back_populates="module")
