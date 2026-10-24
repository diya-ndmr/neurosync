from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Urgency = Literal["STANDARD", "PRIORITY"]
ReferralStatus = Literal[
    "REFERRED", "ASSIGNED", "UNDER_REVIEW", "STUDENT_CONTACTED", "AWAITING_RESPONSE",
    "MEETING_SCHEDULED", "INTERVENTION_ACTIVE", "FOLLOW_UP", "RESOLVED", "CLOSED",
]
InterventionStatus = Literal["PLANNED", "ACTIVE", "FOLLOW_UP", "COMPLETED", "DISCONTINUED"]


class ReferralCreate(BaseModel):
    student_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    module_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
    reason: str = Field(min_length=10, max_length=2000)
    lecturer_notes: Optional[str] = Field(default=None, max_length=4000)
    urgency: Urgency = "STANDARD"


class ReferralStatusUpdate(BaseModel):
    status: ReferralStatus


class RecommendationDecision(BaseModel):
    strategy: str = Field(min_length=3, max_length=120)
    decision: Literal["ACCEPT", "MODIFY", "CHOOSE_DIFFERENT", "DISMISS"]
    reason: str = Field(min_length=5, max_length=2000)
    advisor_notes: Optional[str] = Field(default=None, max_length=4000)
    review_date: Optional[date] = None
    follow_up_date: Optional[date] = None


class CustomStrategyCreate(BaseModel):
    strategy: str = Field(min_length=3, max_length=120)
    reason: str = Field(min_length=5, max_length=2000)
    advisor_notes: Optional[str] = Field(default=None, max_length=4000)
    review_date: Optional[date] = None
    follow_up_date: Optional[date] = None


class InterventionUpdate(BaseModel):
    status: Optional[InterventionStatus] = None
    outcome: Optional[Literal[
        "IMPROVING", "STABLE", "CONTINUED_SUPPORT_REQUIRED", "NO_RESPONSE",
        "REFERRED_TO_OTHER_SUPPORT", "INTERVENTION_COMPLETED",
    ]] = None
    advisor_notes: Optional[str] = Field(default=None, max_length=4000)
    follow_up_date: Optional[date] = None
    review_date: Optional[date] = None


class EmailDraftCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=20, max_length=10000)
    drafted_by_ai: bool = False


class EmailApproval(BaseModel):
    approve: bool


class MeetingCreate(BaseModel):
    meeting_at: datetime
    purpose: str = Field(min_length=3, max_length=500)


class MeetingUpdate(BaseModel):
    status: Literal["MEETING_REQUESTED", "MEETING_SCHEDULED", "MEETING_COMPLETED", "STUDENT_DID_NOT_ATTEND", "MEETING_CANCELLED"]
    advisor_notes: Optional[str] = Field(default=None, max_length=4000)


class AdvisorNoteCreate(BaseModel):
    note: str = Field(min_length=3, max_length=8000)
