"""
NeuroSync Dataset Generator
============================
Generates a realistic synthetic dataset of student records with
features engineered from academic, attendance, behavioural and
wellbeing data. The target variable is the student's risk category
(LOW / MEDIUM / HIGH) derived from a risk score formula.

Output:
    ml/datasets/student_risk_dataset_generated.csv
"""

import os
import random
import numpy as np
import pandas as pd

SEED = 42
N_STUDENTS = 5000
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "student_risk_dataset_generated.csv")


def generate_student(uid: int) -> dict:
    """Generate one synthetic student record."""
    random.seed(SEED + uid)
    np.random.seed(SEED + uid)

    # Base latent "ability" drives most academic features.
    # Distribution shifted lower to produce a realistic spread of risk levels.
    ability = np.clip(np.random.normal(0.55, 0.20), 0.15, 0.95)

    # Academic features
    academic_average = np.clip(ability * 100 + np.random.normal(0, 9), 15, 100)
    assignment_completion = np.clip(np.random.normal(ability * 100, 11), 20, 100)
    failed_module_count = int(np.random.poisson(max(0.0, 2.0 * (1 - ability))))

    # Attendance features
    attendance_percentage = np.clip(np.random.normal(0.45 + ability * 0.55, 0.14), 0.2, 1.0) * 100
    attendance_change = np.clip(np.random.normal(0, 7), -30, 15)

    # Behaviour features
    study_hours_weekly = np.clip(np.random.normal(ability * 20, 7), 0, 40)
    lms_activity_score = np.clip(ability * 100 + np.random.normal(0, 14), 0, 100)

    # Wellbeing features
    mood_average = int(np.clip(np.random.normal(2.5 + ability * 6, 1.7), 1, 10))
    stress_average = int(np.clip(np.random.normal(10.5 - ability * 7, 2.0), 1, 10))

    # Risk score formula (weighted, more aggressive toward risk)
    risk_score = (
        0.32 * (100 - academic_average)
        + 0.26 * (100 - attendance_percentage)
        + 0.14 * max(0, -attendance_change) * 2
        + 0.10 * max(0, 20 - study_hours_weekly) * 2.5
        + 0.09 * (10 - mood_average) * 5
        + 0.09 * (stress_average - 5) * 6
        + 6 * failed_module_count
    )
    risk_score = float(np.clip(risk_score, 0, 100))

    if risk_score <= 40:
        risk_level = "LOW"
    elif risk_score <= 70:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return {
        "student_id": f"NS{uid:06d}",
        "academic_average": round(academic_average, 2),
        "assignment_completion": round(assignment_completion, 2),
        "failed_module_count": failed_module_count,
        "attendance_percentage": round(attendance_percentage, 2),
        "attendance_change": round(attendance_change, 2),
        "study_hours_weekly": round(study_hours_weekly, 2),
        "lms_activity_score": round(lms_activity_score, 2),
        "mood_average": mood_average,
        "stress_average": stress_average,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
    }


def main():
    rows = [generate_student(i) for i in range(N_STUDENTS)]
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset generated: {OUTPUT_PATH}")
    print(f"Rows: {len(df)}")
    print("\nRisk distribution:")
    print(df["risk_level"].value_counts().to_string())


if __name__ == "__main__":
    main()
