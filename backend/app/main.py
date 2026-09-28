from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from .health import get_health, HealthResponse
from .confidence import get_confidence_map, get_timeseries, TimeseriesResponse
from .explanation import get_explanation, ExplanationResponse

app = FastAPI(title="Forecast Bust Detection API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    return get_health()

@app.post("/api/v1/ingest")
def trigger_ingestion():
    from .ingestion import run_ingestion_pipeline, get_ingestion_status
    run_ingestion_pipeline()
    return get_ingestion_status()

@app.get("/api/v1/confidence-map", response_model=Dict[str, Any])
def confidence_map(forecast_date: str, lead_day: int):
    if lead_day < 1 or lead_day > 10:
        raise HTTPException(status_code=400, detail="lead_day must be between 1 and 10")
    return get_confidence_map(forecast_date, lead_day)

@app.get("/api/v1/grid/{grid_id}/timeseries", response_model=TimeseriesResponse)
def timeseries(grid_id: str, forecast_date: str):
    return get_timeseries(grid_id, forecast_date)

@app.get("/api/v1/grid/{grid_id}/explanation", response_model=ExplanationResponse)
def explanation(grid_id: str, forecast_date: str, lead_day: int):
    return get_explanation(grid_id, forecast_date, lead_day)

@app.get("/api/v1/regimes/current")
def regimes_current(forecast_date: str):
    # As per contract, explicitly NOT implemented yet
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Regime clustering not yet available"
    )
