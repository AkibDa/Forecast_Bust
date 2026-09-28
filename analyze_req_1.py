import pandas as pd
import numpy as np

# Load data
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

lats = np.sort(tigge['latitude'].unique())
lons = np.sort(tigge['longitude'].unique())
lat_spacing = np.round(np.diff(lats), 4)
lon_spacing = np.round(np.diff(lons), 4)

print("--- 1. TIGGE Grid ---")
print(f"Unique lat spacing: {np.unique(lat_spacing)}")
print(f"Unique lon spacing: {np.unique(lon_spacing)}")

cells_per_group = tigge.groupby(['init_time', 'lead_time_hours']).size()
print(f"Number of cells per (init, lead) range: {cells_per_group.min()} - {cells_per_group.max()}")

era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
print("\n--- 1. ERA5 tp ---")
import pyarrow.parquet as pq
meta = pq.read_metadata('model/datasets/era5_processed.parquet')
print("Parquet Schema Metadata (attributes):")
# Just print column names, pyarrow metadata doesn't always have simple unit strings
print(era5.columns.tolist())
print(f"Max ERA5 tp: {era5['tp'].max()}, Mean ERA5 tp: {era5['tp'].mean()}")

# Domain-mean tp on overlap days
# Convert ERA5 to mm if it's not already
if era5['tp'].mean() < 1: # Likely in meters
    era5['tp_mm'] = era5['tp'] * 1000.0
else:
    era5['tp_mm'] = era5['tp']

# We need 24h differenced tp for TIGGE
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)

common_dates = np.intersect1d(era5['valid_time'].unique(), tigge['valid_time'].unique())
era5_sub = era5[era5['valid_time'].isin(common_dates)]
tigge_sub = tigge[tigge['valid_time'].isin(common_dates)]

domain_mean_era5 = era5_sub.groupby('valid_time')['tp_mm'].mean()
domain_mean_tigge = tigge_sub.groupby('valid_time')['precip_24h'].mean()

print("\nDomain-mean tp (mm/day) on overlap days:")
for dt in common_dates:
    dt_ts = pd.to_datetime(dt)
    e_val = domain_mean_era5.get(dt, np.nan)
    t_val = domain_mean_tigge.get(dt, np.nan)
    ratio = e_val / t_val if t_val > 0 else np.nan
    print(f"{dt_ts.date()}: ERA5 = {e_val:.4f}, TIGGE 24h = {t_val:.4f} | Ratio = {ratio:.4f}")
