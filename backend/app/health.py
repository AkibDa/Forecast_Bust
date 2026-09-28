import os
import pandas as pd
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .ingestion import get_ingestion_status
from .model_interface import _model, _load_model

class HealthResponse(BaseModel):
    status: str
    model_version: str
    model_loaded: bool
    ingestion_mode: str
    last_success_time: Optional[str]
    last_status: str
    data_coverage_range: Dict[str, str]
    grid_domain: Dict[str, Any]

def get_health() -> HealthResponse:
    ingestion_info = get_ingestion_status()
    
    # Check if model is loaded
    try:
        if _model is None:
            _load_model()
        model_loaded = _model is not None
    except Exception:
        model_loaded = False
        
    # Get historical coverage
    try:
        from .feature_provider import _load_historical_data, _tigge_df
        _load_historical_data()
        min_date = _tigge_df['init_time'].min().date().isoformat()
        max_date = _tigge_df['init_time'].max().date().isoformat()
    except Exception:
        min_date = "unknown"
        max_date = "unknown"
        
    return HealthResponse(
        status="ok",
        model_version="v1",
        model_loaded=model_loaded,
        ingestion_mode=ingestion_info["mode"],
        last_success_time=ingestion_info["last_success_time"],
        last_status=ingestion_info["last_status"],
        data_coverage_range={"start": min_date, "end": max_date},
        grid_domain={
            "lat_min": 8.0,
            "lat_max": 38.0,
            "lon_min": 68.0,
            "lon_max": 103.0,
            "resolution": 0.25,
            "shape": "121x141"
        }
    )
