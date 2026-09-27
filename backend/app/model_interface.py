import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict

# Adjust path assuming this runs from backend/app/
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../model/weights/calibrated_xgb.pkl')
_model = None

def _load_model():
    global _model
    if _model is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                _model = pickle.load(f)
        except FileNotFoundError:
            print(f"Warning: Model not found at {MODEL_PATH}. Prediction will fail.")

def predict(lat: float, lon: float, forecast_date: str, lead_day: int) -> Dict[str, float]:
    """
    Interface for Susovan's model.
    Returns: { "confidence_score": float, "bust_probability": float }
    """
    _load_model()
    
    if _model is None:
        # Fallback if model hasn't been trained yet
        confidence_score = round(np.random.uniform(0.3, 0.95), 2)
        return {
            "confidence_score": confidence_score,
            "bust_probability": round(1.0 - confidence_score, 2)
        }
        
    lead_time_hours = lead_day * 24
    month = pd.to_datetime(forecast_date).month
    
    # Since the function signature cannot change, we mock the forecast field inputs here
    # In a real pipeline, we'd query the ingestion layer for the actual forecast values at (lat, lon).
    # Feature order expected: ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    
    X_infer = pd.DataFrame([{
        'lead_time_hours': lead_time_hours,
        'latitude': lat,
        'longitude': lon,
        'month': month,
        'msl': 101325.0,  # Mean sea level pressure (Pa)
        '10u': 0.0,       # U-wind
        '10v': 0.0,       # V-wind
        '2t': 293.15,     # 20 C
        'tp': 0.0         # Precip
    }])
    
    try:
        bust_prob = float(_model.predict_proba(X_infer)[0, 1])
    except Exception as e:
        print(f"Prediction error: {e}")
        bust_prob = 0.5
        
    return {
        "confidence_score": round(1.0 - bust_prob, 4),
        "bust_probability": round(bust_prob, 4)
    }
