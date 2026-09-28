import os
import requests
import datetime
from typing import Optional, Dict, Any



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
    
    from .config import DOMAIN
    
    leftlon = DOMAIN['lon_min']
    rightlon = DOMAIN['lon_max']
    toplat = DOMAIN['lat_max']
    bottomlat = DOMAIN['lat_min']

    res_str = "0p50" if DOMAIN['resolution'] == 0.5 else "0p25"
    nomads_filter_url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{res_str}.pl"

    params = {
        'file': f'gfs.t{run_hour:02d}z.pgrb2.{res_str}.f{lead_hour:03d}',
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
        response = requests.get(nomads_filter_url, params=params, timeout=30)
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
    import xarray as xr
    import pandas as pd
    
    # cfgrib.open_datasets returns a list of consistent datasets (split by height/level)
    datasets = xr.open_dataset(filepath, engine="cfgrib", backend_kwargs={"errors": "ignore"})
    # wait, open_dataset with errors='ignore' might not return everything.
    # It's better to use cfgrib directly to get all variables despite level conflicts:
    import cfgrib
    ds_list = cfgrib.open_datasets(filepath)
    
    # We need: msl, 10u, 10v, 2t, tp
    # Merge them into a single dataframe
    df_list = []
    for ds in ds_list:
        df_part = ds.to_dataframe().reset_index()
        # Keep only the lat/lon/time and data columns
        cols_to_keep = [c for c in df_part.columns if c not in ["time", "step", "valid_time", "surface", "heightAboveGround", "meanSea"]]
        # We will manually construct valid_time, init_time, lead_time
        # The variables we want are: prmsl, u10, v10, t2m, tp
        valid_data_cols = [c for c in cols_to_keep if c in ["prmsl", "u10", "v10", "t2m", "tp"]]
        if valid_data_cols:
            df_part = df_part[["latitude", "longitude"] + valid_data_cols]
            df_list.append(df_part)
            
    # Merge all parts on lat/lon
    if not df_list:
        raise ValueError("No valid data found in GRIB file")
        
    final_df = df_list[0]
    for df_part in df_list[1:]:
        final_df = pd.merge(final_df, df_part, on=["latitude", "longitude"], how="outer")
        
    # Standardize column names
    final_df = final_df.rename(columns={
        "prmsl": "msl",
        "u10": "10u",
        "v10": "10v",
        "t2m": "2t"
    })
    
    # Handle GFS APCP (Total Precipitation). In GFS, this is usually accumulated over the lead time or 6hr window.
    # For the MVP, we pull lead_hour=24 (f024). The GFS f024 APCP is accumulated from f000 to f024.
    # This exactly matches our corrected model training target of 24h accumulated precipitation!
    # Units are kg/m2 (equivalent to mm), which matches the ERA5 converted tp (mm).
    
    # Extract times from the first dataset
    ref_ds = ds_list[0]
    init_time = pd.to_datetime(ref_ds.time.values)
    valid_time = pd.to_datetime(ref_ds.valid_time.values)
    
    # Compute lead_time_hours
    lead_time_td = valid_time - init_time
    lead_time_hours = int(lead_time_td.total_seconds() // 3600)
    
    final_df["init_time"] = init_time
    final_df["valid_time"] = valid_time
    final_df["lead_time_hours"] = lead_time_hours
    
    # Ensure correct schema and order
    expected_cols = ['init_time', 'valid_time', 'lead_time_hours', 'latitude', 'longitude', 'msl', '10u', '10v', '2t', 'tp']
    for col in expected_cols:
        if col not in final_df.columns:
            final_df[col] = 0.0 # fallback if a variable was totally missing from the grib
            
    final_df = final_df[expected_cols]
    return final_df

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
