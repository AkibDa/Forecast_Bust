import os
import pickle
import pandas as pd
from typing import Dict, Any, List
from fastapi import HTTPException

# Path correctly anchored to __file__
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, '../../model/weights/calibrated_xgb.pkl')
_model = None

def _load_model():
    global _model
    if _model is None:
        try:
            with open(MODEL_PATH, 'rb') as f:
                _model = pickle.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=503, detail="Model weights not found. Ensure model is trained first.")

def predict(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Interface for Susovan's model.
    Accepts a dictionary of features:
    ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    
    Returns: { "confidence_score": float, "bust_probability": float }
    """
    _load_model()
    
    X_infer = pd.DataFrame([features])
    
    # Ensure correct column order
    expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    for col in expected_cols:
        if col not in X_infer.columns:
            X_infer[col] = 0.0
            
    X_infer = X_infer[expected_cols]
    
    bust_prob = float(_model.predict_proba(X_infer)[0, 1])
        
    return {
        "confidence_score": round(1.0 - bust_prob, 4),
        "bust_probability": round(bust_prob, 4)
    }

def predict_batch(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized inference for a batch of cells.
    Returns a DataFrame with ['confidence_score', 'bust_probability'] appended.
    """
    _load_model()
    
    expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    X_infer = features_df[expected_cols].copy()
    
    # Vectorized prediction
    bust_probs = _model.predict_proba(X_infer)[:, 1]
    
    results = features_df.copy()
    results['bust_probability'] = bust_probs.round(4)
    results['confidence_score'] = (1.0 - bust_probs).round(4)
    
    return results
