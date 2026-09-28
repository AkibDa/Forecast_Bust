
import os
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .ingestion import get_ingestion_status
from .model_interface import _model, _load_model
from .config import DOMAIN

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
    try:
        if _model is None:
            _load_model()
        model_loaded = _model is not None
    except Exception:
        model_loaded = False
        
    return HealthResponse(
        status="ok",
        model_version="v1",
        model_loaded=model_loaded,
        ingestion_mode=ingestion_info["mode"],
        last_success_time=ingestion_info["last_success_time"],
        last_status=ingestion_info["last_status"],
        data_coverage_range={"start": "2023-01-01", "end": "2026-09-19"},
        grid_domain=DOMAIN
    )
