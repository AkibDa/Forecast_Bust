
import os
from pydantic import BaseModel
from typing import Optional, Dict, Any
from .ingestion import get_ingestion_status
from .model_interface import _model, _load_model
from .config import DOMAIN
from .feature_provider import get_coverage

class HealthResponse(BaseModel):
    status: str
    model_version: str
    model_loaded: bool
    ingestion_mode: str
    last_success_time: Optional[str]
    last_status: str
    data_coverage_range: Dict[str, Any]
    grid_domain: Dict[str, Any]
    supported_lead_days: list = [1]

def get_health() -> HealthResponse:
    ingestion_info = get_ingestion_status()
    try:
        import backend.app.model_interface as mi
        model_loaded = mi._model is not None
    except Exception:
        model_loaded = False
        
    return HealthResponse(
        status="ok",
        model_version="v1",
        model_loaded=model_loaded,
        ingestion_mode=ingestion_info["mode"],
        last_success_time=ingestion_info["last_success_time"],
        last_status=ingestion_info["last_status"],
        data_coverage_range=get_coverage(),
        grid_domain=DOMAIN,
        supported_lead_days=[1] if ingestion_info["mode"] in ["live", "cache"] else [1,2,3,4,5,6,7,8,9,10]
    )
