from pydantic import BaseModel, ConfigDict
from typing import Optional


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    student_number: str
    first_name: str
    surname: str
    programme: str
    year_level: int
    created_at: str


class PerformancePoint(BaseModel):
    month: str
    average: float


class ModuleBreakdown(BaseModel):
    module: str
    mark: float


class AttendanceHistory(BaseModel):
    month: str
    percentage: float


class RiskFactor(BaseModel):
    factor: str
    impact: str
    direction: str


class RiskPredictionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    risk_score: float
    risk_level: str
    explanation: str
    factors: list[RiskFactor] = []
    model_version: str
    created_at: str


class RecommendationResponse(BaseModel):
    id: str
    category: str
    message: str
    priority: str
    status: str
    created_at: str


class StudentDashboardResponse(BaseModel):
    student: StudentProfileResponse
    performance: Optional[dict] = None
    attendance: Optional[dict] = None
    risk: Optional[RiskPredictionResponse] = None
    recommendations: list[RecommendationResponse] = []
    wellbeing: Optional[dict] = None
