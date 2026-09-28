
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
