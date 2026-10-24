from typing import Literal
from pydantic import BaseModel, Field


class SupportRequestCreate(BaseModel):
    request_type: str = Field(min_length=3, max_length=80)
    message: str = Field(min_length=5, max_length=2000)


class SupportRequestStatusUpdate(BaseModel):
    status: Literal["OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
