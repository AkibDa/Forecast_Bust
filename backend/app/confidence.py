import pandas as pd
from typing import List, Dict, Any
from pydantic import BaseModel
# pyrefly: ignore [missing-import]
from .model_interface import predict, predict_batch
# pyrefly: ignore [missing-import]
from .feature_provider import get_forecast_features, get_forecast_features_batch

class TimeseriesData(BaseModel):
    lead_day: int
    confidence_score: float
    bust_probability: float

class TimeseriesResponse(BaseModel):
    grid_id: str
    latitude: float
    longitude: float
    forecast_date: str
    data_source: str
    lead_times: List[TimeseriesData]

def get_timeseries(grid_id: str, forecast_date: str) -> TimeseriesResponse:
    try:
        lat_str, lon_str = grid_id.split('_')
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Invalid grid_id format. Must be 'lat_lon'")

    lead_times = []
    mode_used = "unknown"
    for day in range(1, 11):
        try:
            features, mode = get_forecast_features(lat, lon, forecast_date, day)
            prediction = predict(features)
            mode_used = mode
            lead_times.append(
                TimeseriesData(
                    lead_day=day,
                    confidence_score=prediction["confidence_score"],
                    bust_probability=prediction["bust_probability"]
                )
            )
        except Exception:
            pass # skip unavailable lead days for timeseries

    return TimeseriesResponse(
        grid_id=grid_id,
        latitude=lat,
        longitude=lon,
        forecast_date=forecast_date,
        data_source=mode_used,
        lead_times=lead_times
    )

def get_confidence_map(forecast_date: str, lead_day: int) -> Dict[str, Any]:
    # Extract features for entire grid in one shot
    features_df, mode = get_forecast_features_batch(forecast_date, lead_day)
    
    # Predict in one shot
    results_df = predict_batch(features_df)
    
    features_list = []
    for _, row in results_df.iterrows():
        lat_r = row['latitude']
        lon_r = row['longitude']
        grid_id = f"{lat_r:.2f}_{lon_r:.2f}"
        
        features_list.append({
            "type": "Feature",
            "geometry": { "type": "Point", "coordinates": [lon_r, lat_r] },
            "properties": {
                "grid_id": grid_id,
                "latitude": lat_r,
                "longitude": lon_r,
                "confidence_score": row["confidence_score"],
                "bust_probability": row["bust_probability"],
                "regime_tag": None
            }
        })
            
    return {
        "type": "FeatureCollection",
        "metadata": {
            "data_source": mode,
            "forecast_date": forecast_date,
            "lead_day": lead_day
        },
        "features": features_list
    }
