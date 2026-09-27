from typing import List, Dict, Any
from pydantic import BaseModel
import numpy as np
from .model_interface import predict
from .feature_provider import get_forecast_features

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
        lat, lon = 23.0, 85.5

    lead_times = []
    for day in range(1, 11):
        features = get_forecast_features(lat, lon, forecast_date, day)
        prediction = predict(features)
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
    features_list = []
    
    # 121x141 grid simulation
    # Use a step of 1.0 to downsample while strictly staying on the 0.25 grid.
    # This ensures exact matches against the parquet datasets without triggering the mock fallback.
    lats = np.arange(8.0, 38.1, 1.0) # 31 points
    lons = np.arange(68.0, 103.1, 1.0) # 36 points
    
    for lat in lats:
        for lon in lons:
            lat_r = round(lat, 2)
            lon_r = round(lon, 2)
            grid_id = f"{lat_r}_{lon_r}"
            
            features = get_forecast_features(lat_r, lon_r, forecast_date, lead_day)
            prediction = predict(features)
            
            features_list.append({
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
        "features": features_list
    }
