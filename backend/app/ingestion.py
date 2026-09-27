import os
import requests
import datetime
from typing import Optional, Dict, Any

# NOMADS GFS filter URL for 0.25 degree resolution
NOMADS_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"

class IngestionStatus:
    last_success_time: Optional[datetime.datetime] = None
    last_status: str = "never_run"
    error_message: Optional[str] = None
    mode: str = "none"

status = IngestionStatus()

def download_latest_gfs(lead_hour: int = 24) -> str:
    """
    Downloads the latest GFS grib2 file for the specified lead time,
    subset to the India region and required variables.
    """
    # GFS takes ~3.5-4 hours after cycle time to publish. Offset time by 4 hours.
    today = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
    run_hour = (today.hour // 6) * 6
    date_str = today.strftime("%Y%m%d")
    
    # Required variables per contract: msl, 10u, 10v, 2t, tp
    leftlon = 68.0
    rightlon = 103.0
    toplat = 38.0
    bottomlat = 8.0

    params = {
        'file': f'gfs.t{run_hour:02d}z.pgrb2.0p25.f{lead_hour:03d}',
        'lev_10_m_above_ground': 'on',
        'lev_2_m_above_ground': 'on',
        'lev_mean_sea_level': 'on',
        'lev_surface': 'on', 
        'var_APCP': 'on',
        'var_PRMSL': 'on',
        'var_TMP': 'on',
        'var_UGRD': 'on',
        'var_VGRD': 'on',
        'subregion': '',
        'leftlon': str(leftlon),
        'rightlon': str(rightlon),
        'toplat': str(toplat),
        'bottomlat': str(bottomlat),
        'dir': f'/gfs.{date_str}/{run_hour:02d}/atmos'
    }

    try:
        print(f"Attempting live NOMADS pull: dir={params['dir']}, file={params['file']}")
        response = requests.get(NOMADS_FILTER_URL, params=params, timeout=30)
        response.raise_for_status()
        
        filepath = f"../model/datasets/gfs_{date_str}_{run_hour:02d}_f{lead_hour:03d}.grb2"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
            
        status.last_success_time = datetime.datetime.utcnow()
        status.last_status = "success"
        status.error_message = None
        status.mode = "live"
        
        # Cache for demo fallback
        cache_path = "../model/datasets/gfs_cached_demo.grb2"
        with open(cache_path, 'wb') as f:
            f.write(response.content)
            
        return filepath

    except Exception as e:
        print(f"Live pull failed ({e}). Attempting fallback to cache...")
        cache_path = "../model/datasets/gfs_cached_demo.grb2"
        if os.path.exists(cache_path):
            status.last_success_time = datetime.datetime.utcnow()
            status.last_status = "success"
            status.error_message = f"Live failed: {e}. Used cache."
            status.mode = "cache"
            return cache_path
            
        status.last_status = "failed"
        status.error_message = str(e)
        status.mode = "none"
        raise e

def process_grib_to_schema(filepath: str):
    """
    Parses the downloaded GRIB2 file using xarray and cfgrib.
    Converts it to the expected dataframe schema: 
    [init_time, valid_time, lead_time_hours, latitude, longitude, msl, 10u, 10v, 2t, tp]
    """
    # NOTE: xarray and cfgrib (requires eccodes C library) are needed for this.
    # This is a stub showing the logic flow.
    # import xarray as xr
    # ds = xr.open_dataset(filepath, engine='cfgrib')
    # df = ds.to_dataframe().reset_index()
    # return df
    pass

def run_ingestion_pipeline():
    try:
        # For MVP, we pull Day 1 (lead hour 24)
        filepath = download_latest_gfs(lead_hour=24)
        process_grib_to_schema(filepath)
    except Exception as e:
        print(f"Ingestion failed: {e}")

def get_ingestion_status() -> Dict[str, Any]:
    return {
        "last_status": status.last_status,
        "last_success_time": status.last_success_time.isoformat() if status.last_success_time else None,
        "error_message": status.error_message,
        "mode": status.mode
    }
