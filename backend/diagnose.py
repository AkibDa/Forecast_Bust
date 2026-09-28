import pandas as pd
import numpy as np
import pickle
from datetime import datetime

# 1. Diagnose near-zero map
print("1. Diagnose near-zero map")
try:
    with open("../model/weights/calibrated_xgb.pkl", "rb") as f:
        calibrator = pickle.load(f)
    
    test_df = pd.read_parquet("../model/datasets/test_split.parquet")
    X_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    X_test = test_df[X_cols]
    
    # IsotonicRegression has a predict method for the calibrator, which returns calibrated probabilities.
    # CalibratedClassifierCV predict_proba returns calibrated probabilities.
    raw_xgb = calibrator.estimator if hasattr(calibrator, 'estimator') else calibrator.base_estimator
    raw_probs = raw_xgb.predict_proba(X_test)[:, 1]
    cal_probs = calibrator.predict_proba(X_test)[:, 1]
    
    print(f"Mean predicted prob on test split: Raw XGBoost: {np.mean(raw_probs):.4f}, Calibrated: {np.mean(cal_probs):.4f}")
    
    # Per-feature mean and std
    train_df = pd.read_parquet("../model/datasets/train_split.parquet")
    print("Training feature stats:")
    for col in X_cols:
        print(f"  {col}: mean={train_df[col].mean():.2f}, std={train_df[col].std():.2f}")
        
    print("Live (2026-09-27) feature stats:")
    import sys
    sys.path.append(".")
    from app.feature_provider import get_forecast_features
    live_features = []
    for lat in np.arange(5, 35.1, 5):
        for lon in np.arange(65, 100.1, 5):
            try:
                ft = get_forecast_features(f"{lat}_{lon}", "2026-09-27T00:00:00", 24, "live")
                live_features.append(ft)
            except Exception:
                pass
    live_df = pd.DataFrame(live_features)
    if len(live_df) > 0:
        for col in X_cols:
            if col in live_df.columns:
                print(f"  {col}: mean={live_df[col].mean():.2f}, std={live_df[col].std():.2f}")
    else:
        print("  No live features found.")
except Exception as e:
    import traceback
    traceback.print_exc()

print("\n3. Historical vs live map exactly matched")
# The previous agent's script did:
# requests.get(f"http://127.0.0.1:8015/api/v1/confidence-map?forecast_date=2023-10-15&lead_day=1")
# but wait! The API endpoint takes `forecast_date`. If it's not in the overlap, what happens?
# `confidence_map` endpoint in app/confidence.py
print("Forecast date used was 2023-10-15. Why did it match live?")
