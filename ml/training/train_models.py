"""
NeuroSync Model Training
========================
Trains three classifiers for academic risk prediction:
    1. Logistic Regression (baseline)
    2. Random Forest
    3. Gradient Boosting

The best-performing model (by weighted F1) is persisted to
`ml/models/` along with the feature scaler.

Run:
    python ml/training/train_models.py
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    f1_score,
    confusion_matrix,
)

# Allow running from repo root or ml/ dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.feature_engineering import (  # noqa: E402
    load_dataset,
    prepare_features,
    get_scaler_and_split,
    FEATURES,
)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def train_and_evaluate():
    print("Loading dataset...")
    df = load_dataset()
    X, y = prepare_features(df)

    print("Splitting data...")
    X_train, X_test, y_train, y_test, scaler = get_scaler_and_split(X, y)

    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42),
    }

    results = {}

    print("\n" + "=" * 60)
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        results[name] = {
            "accuracy": round(float(acc), 4),
            "f1_weighted": round(float(f1), 4),
        }

        print(f"Accuracy: {acc:.4f}")
        print(f"Weighted F1: {f1:.4f}")
        print(classification_report(y_test, y_pred, target_names=["LOW", "MEDIUM", "HIGH"], zero_division=0))
        print("-" * 60)

        joblib.dump(model, os.path.join(MODEL_DIR, f"{name}.joblib"))

    # Persist scaler and feature list
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.joblib"))
    joblib.dump(FEATURES, os.path.join(MODEL_DIR, "features.joblib"))

    # Choose best model by weighted F1
    best_name = max(results, key=lambda k: results[k]["f1_weighted"])
    best_model = models[best_name]
    joblib.dump(best_model, os.path.join(MODEL_DIR, "best_model.joblib"))

    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(
            {
                "results": results,
                "best_model": best_name,
                "feature_list": FEATURES,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print(f"Best model: {best_name} (F1={results[best_name]['f1_weighted']})")
    print(f"Models saved to: {MODEL_DIR}")
    print("Saved: logistic_regression.joblib, random_forest.joblib,")
    print("       gradient_boosting.joblib, best_model.joblib, scaler.joblib, metrics.json")


if __name__ == "__main__":
    train_and_evaluate()

