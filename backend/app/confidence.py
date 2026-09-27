from typing import List, Dict, Any
from pydantic import BaseModel
import numpy as np
from .model_interface import predict

class TimeseriesData(BaseModel):
    lead_day: int
    confidence_score: float
    bust_probability: float

class TimeseriesResponse(BaseModel):
    grid_id: str
    latitude: float
    longitude: float
    forecast_date: str
    lead_times: List[TimeseriesData]

def get_timeseries(grid_id: str, forecast_date: str) -> TimeseriesResponse:
    try:
        lat_str, lon_str = grid_id.split('_')
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        lat, lon = 22.5, 88.25

    lead_times = []
    # Call predict() for Day 1 to 10
    for day in range(1, 11):
        prediction = predict(lat, lon, forecast_date, day)
        lead_times.append(
            TimeseriesData(
                lead_day=day,
                confidence_score=prediction["confidence_score"],
                bust_probability=prediction["bust_probability"]
            )
        )

    return TimeseriesResponse(
        grid_id=grid_id,
        latitude=lat,
        longitude=lon,
        forecast_date=forecast_date,
        lead_times=lead_times
    )

def get_confidence_map(forecast_date: str, lead_day: int) -> Dict[str, Any]:
    features = []
    
    # 121x141 grid simulation
    # Using a subset or downsampled version to keep response times low for the MVP demo
    # We'll step by a larger amount but keep the logic consistent.
    lats = np.linspace(8.0, 38.0, 30) # downsampled from 121 for performance
    lons = np.linspace(68.0, 103.0, 35) # downsampled from 141 for performance
    
    for lat in lats:
        for lon in lons:
            lat_r = round(lat, 2)
            lon_r = round(lon, 2)
            grid_id = f"{lat_r}_{lon_r}"
            prediction = predict(lat_r, lon_r, forecast_date, lead_day)
            
            features.append({
                "type": "Feature",
                "geometry": { "type": "Point", "coordinates": [lon_r, lat_r] },
                "properties": {
                    "grid_id": grid_id,
                    "latitude": lat_r,
                    "longitude": lon_r,
                    "confidence_score": prediction["confidence_score"],
                    "bust_probability": prediction["bust_probability"],
                    "regime_tag": None
                }
            })
            
    return {
        "type": "FeatureCollection",
        "features": features
    }
