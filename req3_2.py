import sys
import os
import requests
import datetime
import pandas as pd
import numpy as np

sys.path.append('backend')
from app.ingestion import process_grib_to_schema

def download_gfs(date_str: str, run_hour: int, lead_hour: int) -> str:
    NOMADS_FILTER_URL = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
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
        'leftlon': '68.0',
        'rightlon': '103.0',
        'toplat': '38.0',
        'bottomlat': '8.0',
        'dir': f'/gfs.{date_str}/{run_hour:02d}/atmos'
    }
    
    filepath = f"model/datasets/gfs_{date_str}_{run_hour:02d}_f{lead_hour:03d}.grb2"
    if not os.path.exists(filepath):
        print(f"Downloading {params['file']} from {params['dir']} ...")
        response = requests.get(NOMADS_FILTER_URL, params=params, timeout=60)
        response.raise_for_status()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(response.content)
    return filepath

print("--- 3. Live Path Lagged Disagreement ---")

# Let's use the most recent 00Z cycle and the one from the day before
today = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
run_hour = 0  # 00Z
date_str_today = today.strftime("%Y%m%d")

yesterday = today - datetime.timedelta(days=1)
date_str_yesterday = yesterday.strftime("%Y%m%d")

try:
    path_today = download_gfs(date_str_today, run_hour, 24)
    df_today = process_grib_to_schema(path_today)
    
    path_yesterday = download_gfs(date_str_yesterday, run_hour, 48)
    df_yesterday = process_grib_to_schema(path_yesterday)
    
    merged = pd.merge(df_today, df_yesterday, on=['latitude', 'longitude'], suffixes=('_today', '_yest'))
    
    for v in ['tp', '2t', 'msl']:
        merged[f'lag_diff_{v}'] = np.abs(merged[f'{v}_today'] - merged[f'{v}_yest'])
        
    print("Values for 3 cells:")
    print(merged[['latitude', 'longitude', 'lag_diff_tp', 'lag_diff_2t', 'lag_diff_msl']].head(3).to_string())
except Exception as e:
    print(f"Error fetching GFS: {e}")
