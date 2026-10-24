"""
NeuroSync Feature Engineering
=============================
Loads raw student data, handles missing values, removes duplicates
and normalizes the feature matrix ready for model training.
"""

import os
from typing import Optional

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

FEATURES = [
    "academic_average",
    "assignment_completion",
    "failed_module_count",
    "attendance_percentage",
    "attendance_change",
    "study_hours_weekly",
    "lms_activity_score",
    "mood_average",
    "stress_average",
]

TARGET = "risk_level"


def load_dataset(path: Optional[str] = None) -> pd.DataFrame:
    if path is None:
        path = os.path.join(
            os.path.dirname(__file__), "..", "datasets", "student_risk_dataset.csv"
        )
    df = pd.read_csv(path)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values, duplicates and invalid rows."""
    df = df.drop_duplicates(subset=["student_id"]).copy()

    df[TARGET] = df[TARGET].astype("string").str.strip().str.upper()

    # Missing values: fill numeric with median
    for col in FEATURES:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Drop rows with invalid target
    df = df[df[TARGET].isin(["LOW", "MEDIUM", "HIGH"])].copy()

    # Clamp risk score to 0-100
    if "risk_score" in df.columns:
        df["risk_score"] = df["risk_score"].clip(0, 100)

    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Extract X (features) and y (encoded target)."""
    df = clean_data(df)
    X = df[FEATURES]
    y = df[TARGET].map({"LOW": 0, "MEDIUM": 1, "HIGH": 2})
    return X, y


def get_scaler_and_split(
    X: pd.DataFrame, y: pd.Series, test_size: float = 0.2
) -> tuple:
    """Standardize features and split into train/test sets."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    scaler = StandardScaler().fit(X_train)
    X_train_scaled = scaler.transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


if __name__ == "__main__":
    data = load_dataset()
    print(f"Raw dataset shape: {data.shape}")
    X, y = prepare_features(data)
    print(f"Features shape: {X.shape}")
    print(f"Target distribution:\n{y.value_counts().to_string()}")
