"""
NeuroSync Risk Prediction Engine
=================================
Loads the trained model and generates explainable risk predictions
from raw student feature values. Returns risk score (0-100),
risk category and human-readable contributing factors.

Risk thresholds:
    0-40  -> LOW
    41-70 -> MEDIUM
    71-100-> HIGH
"""

import os
from typing import List

import joblib
import numpy as np
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class RiskPredictor:
    def __init__(self, model_name: str = "best_model.joblib"):
        self.model = joblib.load(os.path.join(MODEL_DIR, model_name))
        self.scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
        self.features = joblib.load(os.path.join(MODEL_DIR, "features.joblib"))

    def _feature_vector(self, features: dict) -> np.ndarray:
        """Build a raw feature vector in the model's expected order."""
        vector = pd.DataFrame(
            [[features[feature] for feature in self.features]],
            columns=self.features,
        )
        return self.scaler.transform(vector)

    def predict(self, features: dict) -> dict:
        """Return risk category and risk score (0-100) with class probabilities."""
        X = self._feature_vector(features)

        # Map class probabilities (0=LOW, 1=MEDIUM, 2=HIGH) to a 0-100 score
        proba = self.model.predict_proba(X)[0]
        risk_score = float(np.clip(proba[0] * 0 + proba[1] * 55 + proba[2] * 100, 0, 100))

        if risk_score <= 40:
            risk_level = "LOW"
        elif risk_score <= 70:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        explanation = self._build_explanation(features, risk_level)

        return {
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "class_probabilities": {
                "LOW": round(float(proba[0]), 3),
                "MEDIUM": round(float(proba[1]), 3),
                "HIGH": round(float(proba[2]), 3),
            },
            "explanation": explanation,
            "factors": self._list_factors(features),
        }

    @staticmethod
    def _list_factors(features: dict) -> List[dict]:
        """List contributing factors with impact direction."""
        factors = []
        if features.get("attendance_percentage", 100) < 70:
            factors.append({"factor": "Attendance below 70%", "impact": "High", "direction": "increase"})
        if features.get("academic_average", 100) < 50:
            factors.append({"factor": "Average mark below 50%", "impact": "High", "direction": "increase"})
        if features.get("attendance_change", 0) < -5:
            factors.append({"factor": "Attendance declining", "impact": "Medium", "direction": "increase"})
        if features.get("study_hours_weekly", 15) < 10:
            factors.append({"factor": "Reduced study activity", "impact": "Medium", "direction": "increase"})
        if features.get("stress_average", 1) > 8:
            factors.append({"factor": "High stress levels", "impact": "Medium", "direction": "increase"})
        if features.get("mood_average", 5) < 4:
            factors.append({"factor": "Low mood scores", "impact": "Medium", "direction": "increase"})
        if features.get("failed_module_count", 0) > 1:
            factors.append({"factor": "Multiple failed modules", "impact": "High", "direction": "increase"})
        if not factors:
            factors.append({"factor": "Strong academic and wellbeing profile", "impact": "Low", "direction": "decrease"})
        return factors

    @staticmethod
    def _build_explanation(features: dict, risk_level: str) -> str:
        reasons = []
        if features.get("attendance_percentage", 100) < 70:
            reasons.append("attendance below 70%")
        if features.get("academic_average", 100) < 50:
            reasons.append("average mark below 50%")
        if features.get("attendance_change", 0) < -5:
            reasons.append("declining attendance")
        if features.get("study_hours_weekly", 15) < 10:
            reasons.append("reduced study activity")
        if features.get("stress_average", 1) > 8:
            reasons.append("elevated stress levels")
        if features.get("mood_average", 5) < 4:
            reasons.append("low wellbeing scores")
        if features.get("failed_module_count", 0) > 1:
            reasons.append("multiple failed modules")

        if risk_level == "LOW":
            intro = "Student is at low risk of academic failure. "
        elif risk_level == "MEDIUM":
            intro = "Student shows signs of academic risk that should be monitored. "
        else:
            intro = "Student is at high risk of academic failure. "

        if reasons:
            return intro + "Contributing factors: " + "; ".join(reasons) + "."
        return intro + "Current academic, attendance and wellbeing indicators are positive."


def predict_from_features(features: dict, model_name: str = "best_model.joblib") -> dict:
    predictor = RiskPredictor(model_name)
    return predictor.predict(features)


if __name__ == "__main__":
    # Demo prediction
    demo = {
        "academic_average": 48.0,
        "assignment_completion": 55.0,
        "failed_module_count": 2,
        "attendance_percentage": 62.0,
        "attendance_change": -12.0,
        "study_hours_weekly": 6.0,
        "lms_activity_score": 40.0,
        "mood_average": 4,
        "stress_average": 9,
    }
    result = predict_from_features(demo)
    print("Demo prediction:")
    for k, v in result.items():
        print(f"  {k}: {v}")

