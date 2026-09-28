import os
import sys
import pandas as pd
import numpy as np

# 4. Fix the live domain
print("--- 4. Live Domain Fix ---")
sys.path.append('backend')
from app.feature_provider import get_forecast_features_batch
os.environ['ALLOW_CLIMATOLOGY_FALLBACK'] = 'true'
live_df, mode = get_forecast_features_batch('2026-09-27', 1)
print(f"Live feature table lat min/max: {live_df['latitude'].min()} / {live_df['latitude'].max()}")
print(f"Live feature table lon min/max: {live_df['longitude'].min()} / {live_df['longitude'].max()}")
print(f"Number of cells: {len(live_df)}")

cache_file = "model/datasets/gfs_cached_demo.grb2"
if os.path.exists(cache_file):
    os.remove(cache_file)
    print(f"Deleted stale cached GRIB: {cache_file}")

idx_file = cache_file + ".5b7b6.idx"
if os.path.exists(idx_file):
    os.remove(idx_file)

# 5. Month
print("\n--- 5. Month Function ---")
from app.shared_utils import get_month_from_dates
# Print inference value for a sample request
sample_init = '2026-09-27'
sample_lead = 240 # 10 days
inf_month = get_month_from_dates(sample_init, sample_lead)
print(f"Inference month for init='{sample_init}' and lead_time_hours={sample_lead}: {inf_month}")

# Training month distribution
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')
# Thin cells to avoid OOM
sample_lats = tigge['latitude'].unique()[:5]
tigge_sub = tigge[tigge['latitude'].isin(sample_lats)].copy()
tigge_sub['month'] = pd.to_datetime(tigge_sub['valid_time']).dt.month
print("Training month distribution (sampled):")
print(tigge_sub['month'].value_counts().sort_index().to_string())
