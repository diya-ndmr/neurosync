from datetime import date, datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class TopicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)


class TopicFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(min_length=1, max_length=64)
    topic_id: str = Field(min_length=1, max_length=64)
    strengths: list[str] = Field(default_factory=list, max_length=20)
    learning_gaps: list[str] = Field(min_length=1, max_length=20)
    feedback: str = Field(min_length=5, max_length=2000)
    learning_goal: Optional[str] = Field(default=None, max_length=500)
    goal_due_date: Optional[date] = None


class ResourceLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    url: HttpUrl


class LearningProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["viewed", "completed"]


class ClassAttendanceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(min_length=1, max_length=64)
    module_id: str = Field(min_length=1, max_length=64)
    class_name: str = Field(min_length=2, max_length=160)
    class_date: date
    status: Literal["present", "absent", "late", "excused", "approved_leave"]


class WellnessReferralCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_id: str = Field(min_length=1, max_length=64)
    student_message: str = Field(min_length=10, max_length=500)


class AppointmentSlotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)
    location: str = Field(min_length=2, max_length=200)


class AppointmentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["confirmed", "cancelled", "completed", "follow_up"]
    follow_up: Optional[str] = Field(default=None, max_length=500)


class AppointmentSlotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool


class WellnessReferralStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["active", "closed"]


class AppointmentBookingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    referral_id: str = Field(min_length=1, max_length=64)
    slot_id: str = Field(min_length=1, max_length=64)


class UserPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme: Literal["light", "dark", "system"] = "light"
    accent: Literal["blue", "purple", "green", "neutral"] = "blue"
    layout: Literal["comfortable", "compact"] = "comfortable"
    study_reminders: bool = True
    weekly_summary: bool = True
    reminder_frequency: Literal["daily", "weekly", "off"] = "weekly"
    text_size: Literal["default", "large"] = "default"
    dashboard_order: list[str] = Field(default_factory=list, max_length=12)
    preferred_study_start: str = Field(default="18:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(default="Africa/Johannesburg", min_length=1, max_length=64)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Timezone must be a valid IANA timezone") from error
        return value
