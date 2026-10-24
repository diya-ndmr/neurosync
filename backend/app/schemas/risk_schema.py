from pydantic import BaseModel


class PredictionRequest(BaseModel):
    student_id: str


class PredictionResponse(BaseModel):
    risk_level: str
    risk_score: float
    explanation: str
    factors: list[dict] = []
    model_version: str = "gradient_boost_v1.0"
