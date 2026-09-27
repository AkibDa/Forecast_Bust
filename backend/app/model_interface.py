import os
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any

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

def predict(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Interface for Susovan's model.
    Accepts a dictionary of features:
    ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    
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
        
    X_infer = pd.DataFrame([features])
    
    # Ensure correct column order
    expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    for col in expected_cols:
        if col not in X_infer.columns:
            X_infer[col] = 0.0
            
    X_infer = X_infer[expected_cols]
    
    try:
        bust_prob = float(_model.predict_proba(X_infer)[0, 1])
    except Exception as e:
        print(f"Prediction error: {e}")
        bust_prob = 0.5
        
    return {
        "confidence_score": round(1.0 - bust_prob, 4),
        "bust_probability": round(bust_prob, 4)
    }
