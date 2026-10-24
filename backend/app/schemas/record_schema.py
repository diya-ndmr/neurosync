"""Request models for the flat academic-record endpoints.

These replace untyped ``dict`` request bodies. Without validation, an unknown or
missing field reached the ORM constructor (``Model(**data)``) and surfaced as an
unhandled ``TypeError`` — an HTTP 500 that leaked a server traceback for what is
really a client mistake. Typed models answer with a 422 validation error, and
``extra="forbid"`` stops a typo from ever reaching the database layer.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=64)
    module_id: str = Field(min_length=1, max_length=64)
    attendance_percentage: float = Field(ge=0, le=100)
    date: date


class AssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=64)
    module_id: str = Field(min_length=1, max_length=64)
    assessment_type: str = Field(min_length=1, max_length=64)
    mark: float = Field(ge=0, le=100)
    assessment_date: date


class StudySessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=120)
    duration_minutes: int = Field(gt=0, le=1440)
    activity_type: str = Field(min_length=1, max_length=64)


class ModuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module_code: str = Field(min_length=2, max_length=32)
    module_name: str = Field(min_length=2, max_length=200)
    faculty: str = Field(default="Computing", min_length=2, max_length=120)


class WellbeingCheckinCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=64)
    mood_score: int = Field(default=5, ge=1, le=10)
    stress_level: int = Field(default=5, ge=1, le=10)
    notes: Optional[str] = Field(default=None, max_length=2000)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: str = Field(min_length=1, max_length=64)
