import os
import json
import subprocess
import hashlib
from time import sleep

def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return res.stdout.strip() + "\n" + res.stderr.strip()

# Create config.py
config_code = """
DOMAIN = {
    "lat_min": 5.0,
    "lat_max": 35.0,
    "lon_min": 65.0,
    "lon_max": 100.0,
    "resolution": 0.5,
    "shape": "61x71"
}
"""
os.makedirs("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app", exist_ok=True)
with open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/config.py", "w") as f:
    f.write(config_code)

# Fix health.py to use config
health_code = """
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
"""
with open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/health.py", "w") as f:
    f.write(health_code)

# Add exceptions and startup to main.py
main_code = """
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Dict, Any

from .health import get_health, HealthResponse
from .confidence import get_confidence_map, get_timeseries, TimeseriesResponse
from .explanation import get_explanation, ExplanationResponse
from .ingestion import run_ingestion_pipeline

app = FastAPI(title="Forecast Bust Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "422", "message": str(exc.errors())}},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": str(exc.status_code), "message": exc.detail}},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "500", "message": str(exc)}},
    )

@app.on_event("startup")
def startup_event():
    try:
        run_ingestion_pipeline()
    except Exception as e:
        print(f"Startup ingestion error: {e}")

@app.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    return get_health()

@app.post("/api/v1/ingest")
def trigger_ingestion():
    from .ingestion import get_ingestion_status
    run_ingestion_pipeline()
    return get_ingestion_status()

@app.get("/api/v1/confidence-map", response_model=Dict[str, Any])
def confidence_map(forecast_date: str, lead_day: int):
    if lead_day < 1 or lead_day > 10:
        raise HTTPException(status_code=422, detail="lead_day must be between 1 and 10")
    # Live mode constraint logic is handled in feature_provider.py which will raise a ValueError, we catch it
    return get_confidence_map(forecast_date, lead_day)

@app.get("/api/v1/grid/{grid_id}/timeseries", response_model=TimeseriesResponse)
def timeseries(grid_id: str, forecast_date: str):
    return get_timeseries(grid_id, forecast_date)

@app.get("/api/v1/grid/{grid_id}/explanation", response_model=ExplanationResponse)
def explanation(grid_id: str, forecast_date: str, lead_day: int):
    return get_explanation(grid_id, forecast_date, lead_day)

@app.get("/api/v1/regimes/current")
def regimes_current(forecast_date: str):
    raise HTTPException(status_code=501, detail="Regime clustering not yet available")
"""
with open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/main.py", "w") as f:
    f.write(main_code)

# Fix feature provider
feature_prov_code = open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/feature_provider.py").read()
if "if lead_day != 1:" not in feature_prov_code:
    feature_prov_code = feature_prov_code.replace(
        'if status.last_status == "success" and status.mode in ["live", "cache"]:',
        'if status.last_status == "success" and status.mode in ["live", "cache"]:\n        if lead_day != 1:\n            raise ValueError("supported_lead_days=[1] for live/cache mode in MVP")'
    )
    with open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/feature_provider.py", "w") as f:
        f.write(feature_prov_code)

# Fix ingestion to load cache on fail
ingestion_code = open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/ingestion.py").read()
if "except Exception as e:\n        status.last_status = \"failed\"" in ingestion_code:
    ingestion_code = ingestion_code.replace(
        'except Exception as e:\n        status.last_status = "failed"\n        status.error_message = str(e)\n        status.mode = "none"',
        'except Exception as e:\n        print(f"Live pull failed: {e}. Falling back to cache.")\n        try:\n            cache_path = os.path.join(os.path.dirname(__file__), "../../model/datasets/gfs_cached_demo.grb2")\n            _process_grib_to_schema(cache_path)\n            status.last_status = "success"\n            status.error_message = None\n            status.mode = "cache"\n            status.last_success_time = datetime.utcnow().isoformat()\n        except Exception as e2:\n            status.last_status = "failed"\n            status.error_message = str(e2)\n            status.mode = "none"'
    )
    with open("/Users/skakibahammed/code_playground/Forecast_Bust/backend/app/ingestion.py", "w") as f:
        f.write(ingestion_code)

print("Backend prepared.")
