from pydantic import BaseModel, ConfigDict, Field


class AdminIntelligenceQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)


class AdminAnalyticsResponse(BaseModel):
    total_students: int
    active_students: int
    average_performance: float
    retention_rate: float
    high_risk_students: int
    risk_distribution: list[dict] = []
    attendance_trend: list[dict] = []
    performance_trend: list[dict] = []
    programme_comparison: list[dict] = []
