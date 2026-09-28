import os

def get_coverage(mode: str = None):
    _load_historical_data()
    historical_dates = sorted(_tigge_df['init_time'].dt.strftime('%Y-%m-%d').unique().tolist())
    from .ingestion import status
    live_cycle = []
    if status.last_status == "success" and status.mode in ["live", "cache"] and status.last_success_time:
        if isinstance(status.last_success_time, str):
            live_cycle = [status.last_success_time.split("T")[0]]
        else:
            live_cycle = [status.last_success_time.strftime("%Y-%m-%d")]
    
    if mode == "historical":
        return historical_dates
    elif mode == "live":
        return live_cycle
    return {"historical": historical_dates, "live": live_cycle}

import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
from fastapi import HTTPException
from .shared_utils import get_month_from_dates
import numpy as np

BASE_DIR = os.path.dirname(__file__)
TIGGE_PATH = os.path.join(BASE_DIR, '../../model/datasets/tigge_ncep_2023_2024.parquet')
_tigge_df = None

def _load_historical_data():
    global _tigge_df
    if _tigge_df is None:
        try:
            _tigge_df = pd.read_parquet(TIGGE_PATH)
            # Add an init_time column for easier filtering if it doesn't exist
            if 'init_time' not in _tigge_df.columns:
                _tigge_df['init_time'] = pd.to_datetime(_tigge_df['valid_time']) - pd.to_timedelta(_tigge_df['lead_time_hours'], unit='h')
            
            # Apply diff to precipitation so it's 24h instead of accumulated since init
            _tigge_df = _tigge_df.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
            _tigge_df['precipitation'] = _tigge_df.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(_tigge_df['precipitation']).clip(lower=0)
        except Exception as e:
            print(f"Failed to load historical TIGGE data: {e}")
            raise HTTPException(status_code=503, detail="Historical database unavailable.")

def determine_routing_mode(forecast_date: str) -> str:
    """
    Determines whether to use 'live' or 'historical' path.
    Live: within the last 5 days.
    Historical: before 2025 (or demo historical dates).
    """
    forecast_dt = pd.to_datetime(forecast_date)
    now = pd.to_datetime('today')
    if (now - forecast_dt).days <= 5 and forecast_dt.year >= 2026:
        return "live"
    return "historical"

def get_forecast_features_batch(forecast_date: str, lead_day: int) -> Tuple[pd.DataFrame, str]:
    """
    Batch feature extraction for the entire grid. Returns a DataFrame of all cells and the routing mode.
    """
    mode = determine_routing_mode(forecast_date)
    lead_time_hours = lead_day * 24
    forecast_dt = pd.to_datetime(forecast_date)
    
    from .config import DOMAIN
    
    # 61x71 grid (0.5 degree resolution)
    lats = pd.Series(np.arange(DOMAIN['lat_min'], DOMAIN['lat_max'] + DOMAIN['resolution'], DOMAIN['resolution']).round(2))
    lons = pd.Series(np.arange(DOMAIN['lon_min'], DOMAIN['lon_max'] + DOMAIN['resolution'], DOMAIN['resolution']).round(2))
    grid_df = pd.MultiIndex.from_product([lats, lons], names=['latitude', 'longitude']).to_frame(index=False)
    grid_df['init_time'] = forecast_dt
    grid_df['lead_time_hours'] = lead_time_hours
    grid_df['month'] = get_month_from_dates(forecast_dt, lead_time_hours)

    if mode == "historical":
        _load_historical_data()
        
        # Filter on exact init_time and lead_time_hours
        slice_df = _tigge_df[
            (_tigge_df['init_time'] == forecast_dt) & 
            (_tigge_df['lead_time_hours'] == lead_time_hours)
        ].copy()
        
        if slice_df.empty:
            historical_cov = get_coverage('historical')
            raise HTTPException(
                status_code=404, 
                detail=f"Historical data not found for init_time={forecast_date} and lead_day={lead_day}. Available dates range from {historical_cov[0]} to {historical_cov[-1]}"
            )
            
        slice_df['latitude'] = slice_df['latitude'].round(2)
        slice_df['longitude'] = slice_df['longitude'].round(2)
        
        merged = pd.merge(grid_df, slice_df, on=['latitude', 'longitude', 'lead_time_hours'], how='left')
        
        # We must drop cells outside the domain (i.e. NaNs after merge)
        merged = merged.dropna(subset=['mslp'])
        
        rename_dict = {'mslp': 'msl', 'u10': '10u', 'v10': '10v', 'temperature_2m': '2t', 'precipitation': 'tp'}
        merged = merged.rename(columns=rename_dict)
        return merged, mode

    elif mode == "live":
        # Check if live ingestion ran
        from .ingestion import status, process_grib_to_schema
        
        if status.last_status == "success" and status.mode in ["live", "cache"]:
            try:
                # the file path was stored in last success, but we can't easily retrieve it from just the status struct if it's transient.
                # However, download_latest_gfs sets cache path. Let's just use the cached path for demo since we know it exists.
                # In production, we'd look up the exact parsed db table.
                cache_path = os.path.join(BASE_DIR, "../../model/datasets/gfs_cached_demo.grb2")
                live_df = process_grib_to_schema(cache_path)
                
                # Filter to the requested lead time
                live_df = live_df[live_df['lead_time_hours'] == lead_time_hours].copy()
                if live_df.empty:
                    # GFS files are individual per lead hour. In our MVP we only downloaded f024 (lead_day=1).
                    if lead_day != 1:
                        raise HTTPException(status_code=404, detail="Live API currently only stores lead_day=1 (f024) in this MVP.")
                
                live_df['latitude'] = live_df['latitude'].round(2)
                live_df['longitude'] = live_df['longitude'].round(2)
                merged = pd.merge(grid_df, live_df, on=['latitude', 'longitude', 'lead_time_hours'], how='left')
                merged = merged.dropna(subset=['msl'])
                return merged, mode
            except Exception as e:
                # If parsing fails or we allow climatology
                allow_climatology = os.getenv("ALLOW_CLIMATOLOGY_FALLBACK", "false").lower() == "true"
                if not allow_climatology:
                    raise HTTPException(status_code=503, detail=f"Live ingestion data parsing failed: {e}. Climatology fallback is disabled.")
                mode = "climatology_fallback"
        else:
            allow_climatology = os.getenv("ALLOW_CLIMATOLOGY_FALLBACK", "false").lower() == "true"
            if not allow_climatology:
                raise HTTPException(status_code=503, detail="Live ingestion data unavailable and climatology fallback is disabled.")
            mode = "climatology_fallback"

        # Fallback to climatology
        _load_historical_data()
        climatology_df = _tigge_df.groupby(['latitude', 'longitude']).mean(numeric_only=True).reset_index()
        climatology_df['latitude'] = climatology_df['latitude'].round(2)
        climatology_df['longitude'] = climatology_df['longitude'].round(2)
        
        merged = pd.merge(grid_df, climatology_df, on=['latitude', 'longitude'], how='left')
        merged = merged.dropna(subset=['mslp'])
        
        rename_dict = {'mslp': 'msl', 'u10': '10u', 'v10': '10v', 'temperature_2m': '2t', 'precipitation': 'tp'}
        merged = merged.rename(columns=rename_dict)
        return merged, mode

def get_forecast_features(lat: float, lon: float, forecast_date: str, lead_day: int) -> Tuple[Dict[str, Any], str]:
    """
    Single-cell fallback extraction, returning the dict and the mode.
    Used by /timeseries.
    """
    mode = determine_routing_mode(forecast_date)
    lead_time_hours = lead_day * 24
    forecast_dt = pd.to_datetime(forecast_date)
    month = get_month_from_dates(forecast_dt, lead_time_hours)
    
    if mode == "historical":
        _load_historical_data()
        row = _tigge_df[
            (_tigge_df['init_time'] == forecast_dt) &
            (_tigge_df['lead_time_hours'] == lead_time_hours) &
            (_tigge_df['latitude'].round(2) == round(lat, 2)) &
            (_tigge_df['longitude'].round(2) == round(lon, 2))
        ]
        
        if row.empty:
            raise HTTPException(status_code=404, detail=f"Grid cell {lat}_{lon} not found in historical data or outside domain.")
            
        data = row.iloc[0]
        return {
            'lead_time_hours': lead_time_hours,
            'latitude': lat,
            'longitude': lon,
            'month': month,
            'msl': float(data['mslp']),
            '10u': float(data['u10']),
            '10v': float(data['v10']),
            '2t': float(data['temperature_2m']),
            'tp': float(data['precipitation'])
        }, mode

    # If live/climatology fallback
    return _live_single_cell_logic(lat, lon, forecast_date, lead_day, month, mode)

def _live_single_cell_logic(lat, lon, forecast_date, lead_day, month, mode):
    lead_time_hours = lead_day * 24
    from .ingestion import status, process_grib_to_schema
    if status.last_status == "success" and status.mode in ["live", "cache"]:
        try:
            cache_path = os.path.join(BASE_DIR, "../../model/datasets/gfs_cached_demo.grb2")
            live_df = process_grib_to_schema(cache_path)
            live_df = live_df[live_df['lead_time_hours'] == lead_time_hours]
            if live_df.empty:
                if lead_day != 1:
                    raise HTTPException(status_code=404, detail="Live API currently only stores lead_day=1 (f024) in this MVP.")
            
            row = live_df[
                (live_df['latitude'].round(2) == round(lat, 2)) &
                (live_df['longitude'].round(2) == round(lon, 2))
            ]
            if not row.empty:
                data = row.iloc[0]
                return {
                    'lead_time_hours': lead_time_hours,
                    'latitude': lat,
                    'longitude': lon,
                    'month': month,
                    'msl': float(data['msl']),
                    '10u': float(data['10u']),
                    '10v': float(data['10v']),
                    '2t': float(data['2t']),
                    'tp': float(data['tp'])
                }, mode
        except Exception:
            pass # fall through to climatology

    allow_climatology = os.getenv("ALLOW_CLIMATOLOGY_FALLBACK", "false").lower() == "true"
    if not allow_climatology:
        raise HTTPException(status_code=503, detail="Live ingestion data unavailable and climatology fallback is disabled.")
    
    _load_historical_data()
    cell_rows = _tigge_df[
        (_tigge_df['latitude'].round(2) == round(lat, 2)) &
        (_tigge_df['longitude'].round(2) == round(lon, 2))
    ]
    if cell_rows.empty:
        raise HTTPException(status_code=404, detail="Grid cell outside domain.")
        
    data = cell_rows.mean(numeric_only=True)
    return {
        'lead_time_hours': lead_time_hours,
        'latitude': lat,
        'longitude': lon,
        'month': month,
        'msl': float(data['mslp']),
        '10u': float(data['u10']),
        '10v': float(data['v10']),
        '2t': float(data['temperature_2m']),
        'tp': float(data['precipitation'])
    }, "climatology_fallback"
