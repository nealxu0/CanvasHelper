# backend/train_model.py
"""
Train a RandomForestRegressor pipeline on the engineered training data
and save the fitted pipeline using joblib.

- Loads the first available CSV from DATA_PATHS.
- Uses features: weight, vle_count_total, past_avg_score, assessment_type (if present).
- Target: assignment_hours
- Saves pipeline to backend/models/schedule_model.pkl
"""

import os
from pathlib import Path
import json
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# Candidate data file locations (first existing file will be used)
DATA_PATHS = [
    Path("backend/training_data/oulad_training.csv"),
    Path("backend/training_data/cleaned_students_performance.csv"),
    Path("backend/training_data/combined_assignments.csv"),
]

MODEL_OUT_DIR = Path("backend/models")
MODEL_OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_OUT_PATH = MODEL_OUT_DIR / "schedule_model.pkl"
METRICS_OUT_PATH = MODEL_OUT_DIR / "training_metrics.json"

def find_data_file():
    for p in DATA_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(f"No training CSV found. Looked for: {DATA_PATHS}")

def main():
    data_fp = find_data_file()
    df = pd.read_csv(data_fp)

    # Determine expected features
    expected_features = []
    if 'weight' in df.columns:
        expected_features.append('weight')
    if 'vle_count_total' in df.columns:
        expected_features.append('vle_count_total')
    if 'past_avg_score' in df.columns:
        expected_features.append('past_avg_score')
    if 'assessment_type' in df.columns:
        expected_features.append('assessment_type')

    if 'assignment_hours' not in df.columns:
        raise KeyError("Target column 'assignment_hours' not found in dataset.")

    if not expected_features:
        raise KeyError("No expected features found in dataset. Check CSV columns.")

    X = df[expected_features].copy()
    y = df['assignment_hours'].astype(float)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    numeric_cols = [c for c in expected_features if c != 'assessment_type']
    categorical_cols = [c for c in expected_features if c == 'assessment_type']

    # Preprocessing pipelines
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="mean")),
        ("scaler", StandardScaler())
    ])

    categorical_pipeline = None
    if categorical_cols:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])

    transformers = [("num", numeric_pipeline, numeric_cols)]
    if categorical_cols and categorical_pipeline is not None:
        transformers.append(("cat", categorical_pipeline, categorical_cols))

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0
    )

    # Full pipeline with RandomForest
    pipeline = Pipeline([
        ("pre", preprocessor),
        ("rf", RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1))
    ])

    # Train
    pipeline.fit(X_train, y_train)

    # Predict and evaluate (metrics are computed but not printed)
    y_pred = pipeline.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))

    # Cross-validated R^2 (best-effort, may be slow)
    cv_mean = None
    cv_std = None
    try:
        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="r2", n_jobs=-1)
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    except Exception:
        cv_mean = None
        cv_std = None

    # Feature importances extraction (best-effort)
    feature_importances = None
    try:
        feature_names = []
        feature_names.extend(numeric_cols)
        if categorical_cols:
            # get one-hot names
            ohe = pipeline.named_steps["pre"].named_transformers_["cat"].named_steps["onehot"]
            cat_ohe_names = list(ohe.get_feature_names_out(categorical_cols))
            feature_names.extend(cat_ohe_names)

        importances = pipeline.named_steps["rf"].feature_importances_
        feature_importances = [
            {"feature": name, "importance": float(imp)}
            for name, imp in zip(feature_names, importances)
        ]
        # sort descending
        feature_importances = sorted(feature_importances, key=lambda x: x["importance"], reverse=True)
    except Exception:
        feature_importances = None

    # Save trained pipeline
    joblib.dump(pipeline, MODEL_OUT_PATH)

    # Save training metrics and metadata for later use
    metrics = {
        "data_file": str(data_fp),
        "n_samples": int(len(df)),
        "features": expected_features,
        "target": "assignment_hours",
        "r2_test": r2,
        "mae_test": mae,
        "rmse_test": rmse,
        "cv_r2_mean": cv_mean,
        "cv_r2_std": cv_std,
        "feature_importances": feature_importances
    }
    # Write metrics json (overwrites if exists)
    with open(METRICS_OUT_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    main()
