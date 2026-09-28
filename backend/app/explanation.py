import os
import pickle
import numpy as np
import pandas as pd
import shap
from typing import List, Optional
from pydantic import BaseModel
from sklearn.neighbors import NearestNeighbors
from . import model_interface
from .feature_provider import get_forecast_features

class Driver(BaseModel):
    feature: str
    contribution: float
    direction: str

class Analog(BaseModel):
    case_date: str
    event_name: str
    similarity_score: float
    historical_error_summary: str

class ExplanationResponse(BaseModel):
    grid_id: str
    lead_day: int
    regime_tag: Optional[str] = None
    top_drivers: List[Driver]
    analogs: List[Analog]

# --- Load Analog Index ---
ANALOG_PATH = os.path.join(os.path.dirname(__file__), '../../model/weights/analog_index.pkl')
_analog_data = None
_nn_model = None

def _load_analog_index():
    global _analog_data, _nn_model
    if _analog_data is None:
        try:
            with open(ANALOG_PATH, 'rb') as f:
                _analog_data = pickle.load(f)
            _nn_model = NearestNeighbors(n_neighbors=3, metric='cosine')
            _nn_model.fit(_analog_data['embeddings'])
        except Exception as e:
            print(f"Warning: Failed to load analog index: {e}")

_explainer = None
def _load_explainer():
    global _explainer
    if _explainer is None:
        model_interface._load_model()
        if model_interface._model is not None:
            if hasattr(model_interface._model, 'calibrated_classifiers_'):
                xgb_model = model_interface._model.calibrated_classifiers_[0].estimator
            elif hasattr(model_interface._model, 'estimator'):
                xgb_model = model_interface._model.estimator
            else:
                xgb_model = model_interface._model
                
            _explainer = shap.TreeExplainer(xgb_model)

def get_explanation(grid_id: str, forecast_date: str, lead_day: int) -> ExplanationResponse:
    try:
        lat_str, lon_str = grid_id.split('_')
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Invalid grid_id format. Must be 'lat_lon'")

    features_dict, _ = get_forecast_features(lat, lon, forecast_date, lead_day)
    
    # Expected order: ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
    X_infer = pd.DataFrame([features_dict], columns=expected_cols).fillna(0)
    
    # 1. Real SHAP Feature Contributions
    _load_explainer()
    top_drivers = []
    
    if _explainer is not None:
        shap_values = _explainer.shap_values(X_infer)
        
        # If binary classification, shap_values is a list [class_0, class_1] in some old versions, 
        # but in newer tree explainer it's a single array or list of arrays.
        if isinstance(shap_values, list):
            sv = shap_values[1][0] # class 1
        else:
            if len(shap_values.shape) == 3:
                sv = shap_values[0, :, 1]
            else:
                sv = shap_values[0]
                
        # Map back to canonical names
        feature_map = {
            'msl': 'mslp',
            '10u': 'u10',
            '10v': 'v10',
            '2t': 't2m',
            'tp': 'precip'
        }
        
        contributions = []
        for i, col in enumerate(expected_cols):
            if col in feature_map:
                contributions.append((feature_map[col], sv[i]))
                
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        
        for feat, contrib in contributions[:3]:
            # A positive SHAP value for class 1 (bust) means it INCREASES bust probability, 
            # which LOWERS confidence.
            direction = "lowers_confidence" if contrib > 0 else "raises_confidence"
            top_drivers.append(Driver(
                feature=feat,
                contribution=round(float(contrib), 4),
                direction=direction
            ))
    else:
        raise HTTPException(status_code=503, detail="Explainer model unavailable.")

    # 2. Real Analog Retrieval
    _load_analog_index()
    analogs = []
    
    if _analog_data is not None and _nn_model is not None:
        from .feature_provider import get_forecast_features_batch
        
        # Pull the entire grid for this date/lead to compute the spatial embedding
        try:
            batch_df, _ = get_forecast_features_batch(forecast_date, lead_day)
            
            lats = _analog_data['lats']
            lons = _analog_data['lons']
            pca = _analog_data['pca']
            
            # Subset and pivot exactly like build_analog_index.py
            subset = batch_df[(batch_df['latitude'].isin(lats)) & (batch_df['longitude'].isin(lons))]
            
            # To ensure the exact column alignment, we generate all expected column multi-index tuples
            import itertools
            expected_pairs = list(itertools.product(sorted(lats), sorted(lons)))
            
            # Extract tp values, defaulting to 0 for missing cells
            query_vector = []
            lookup = subset.set_index(['latitude', 'longitude'])['tp'].to_dict()
            for lat_val, lon_val in expected_pairs:
                query_vector.append(lookup.get((lat_val, lon_val), 0.0))
                
            query_array = np.array(query_vector).reshape(1, -1)
            
            # Note: The query is built strictly from the forecast 'tp' values for the matching coarse grid.
            # Magnitudes and variance match the ERA5 precipitation processing pipeline.
            query_embedding = pca.transform(query_array)
            
            # Pad to 32 if necessary, exactly like build_analog_index
            if query_embedding.shape[1] < 32:
                pad = np.zeros((1, 32 - query_embedding.shape[1]))
                query_embedding = np.hstack([query_embedding, pad])
            
            distances, indices = _nn_model.kneighbors(query_embedding)
            
            for rank, idx in enumerate(indices[0]):
                similarity = round(max(0.0, 1.0 - distances[0][rank]), 2)
                date_str = _analog_data['dates'][idx].split(' ')[0]
                analogs.append(Analog(
                    case_date=date_str,
                    event_name=_analog_data['events'][idx],
                    similarity_score=similarity,
                    historical_error_summary=f"Historical analog matched with similarity {similarity:.2f}"
                ))
        except Exception as e:
            # If batch fails or data missing, bubble up the HTTP exception
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Failed to generate analog embedding: {e}")
    else:
        raise HTTPException(status_code=503, detail="Analog index unavailable.")

    return ExplanationResponse(
        grid_id=grid_id,
        lead_day=lead_day,
        regime_tag=None, 
        top_drivers=top_drivers,
        analogs=analogs
    )
