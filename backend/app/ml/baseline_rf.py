import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error, r2_score

MODEL_FILE = os.path.join(os.path.dirname(__file__), "rf_model.pkl")
DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")

# Core Feature Columns used for training and prediction
FEATURE_COLS = ["crime_score", "lighting_score", "cctv_density", "crowd_density"]
TARGET_COL = "safety_score"

_rf_model: RandomForestRegressor = None

def load_dataset() -> pd.DataFrame:
    """Load dataset from mumbai_safety_network.json as a pandas DataFrame."""
    if not os.path.exists(DATASET_FILE):
        raise FileNotFoundError(f"Dataset file not found at: {DATASET_FILE}")

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data["segments"])
    return df

def train_baseline_rf_model() -> Tuple[RandomForestRegressor, Dict[str, float]]:
    """Train Random Forest model and return (model, metrics_dict)."""
    global _rf_model
    df = load_dataset()

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    metrics = {
        "rmse": float(round(rmse, 4)),
        "r2_score": float(round(r2, 4)),
        "num_train_samples": len(X_train),
        "num_test_samples": len(X_test)
    }

    # Save serialized model to disk
    joblib.dump(rf, MODEL_FILE)
    _rf_model = rf

    print(f"[Random Forest Baseline] Model trained successfully.")
    print(f"[Random Forest Baseline] Test RMSE: {metrics['rmse']}, R2 Score: {metrics['r2_score']}")

    return rf, metrics

def get_rf_model() -> RandomForestRegressor:
    """Load cached model or train if not present."""
    global _rf_model
    if _rf_model is not None:
        return _rf_model

    if os.path.exists(MODEL_FILE):
        try:
            _rf_model = joblib.load(MODEL_FILE)
            return _rf_model
        except Exception:
            pass

    # Fallback to training
    model, _ = train_baseline_rf_model()
    return model

def predict_safety_score(crime_score: float, lighting_score: float, cctv_density: float, crowd_density: float) -> float:
    """Predict composite safety score (0 to 100) using Random Forest model."""
    rf = get_rf_model()
    features_df = pd.DataFrame([[crime_score, lighting_score, cctv_density, crowd_density]], columns=FEATURE_COLS)
    pred = rf.predict(features_df)[0]
    return float(round(max(0.0, min(100.0, pred)), 2))


if __name__ == "__main__":
    train_baseline_rf_model()
