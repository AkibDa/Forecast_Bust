import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

tigge = pd.read_parquet('../model/datasets/tigge_ncep_2023_2024.parquet')
era5 = pd.read_parquet('../model/datasets/era5_processed.parquet')

# 1. ERA5 stats
print("1. ERA5:")
print(f"min/max valid_time: {era5['valid_time'].min()} / {era5['valid_time'].max()}")
print(f"# distinct dates: {era5['valid_time'].dt.date.nunique()}")

# 2. TIGGE stats
print("\n2. TIGGE:")
if 'init_time' in tigge.columns:
    print(f"min/max init_time: {tigge['init_time'].min()} / {tigge['init_time'].max()}")
elif 'forecast_date' in tigge.columns:
    print(f"min/max init_time: {tigge['forecast_date'].min()} / {tigge['forecast_date'].max()}")

print(f"distinct lead_time_hours: {sorted(tigge['lead_time_hours'].unique())}")
# Hours of day of valid_time
if 'valid_time' in tigge.columns:
    print(f"hours-of-day of valid_time: {sorted(tigge['valid_time'].dt.hour.unique())}")
else:
    tigge['valid_time'] = pd.to_datetime(tigge.get('forecast_date', tigge.get('init_time'))) + pd.to_timedelta(tigge['lead_time_hours'], unit='h')
    print(f"hours-of-day of valid_time: {sorted(tigge['valid_time'].dt.hour.unique())}")

# 3. Overlap
overlap = set(tigge['valid_time'].unique()).intersection(set(era5['valid_time'].unique()))
print(f"\n3. Overlap:\ncount: {len(overlap)}\nlist: {sorted(list(overlap))}")

# 4. Samples
print("\n4. Normalization samples per (lat, lon, lead) group:")
if len(overlap) > 0:
    merged = pd.merge(tigge, era5, on=['valid_time', 'latitude', 'longitude'])
    group_counts = merged.groupby(['latitude', 'longitude', 'lead_time_hours']).size()
    print(f"min: {group_counts.min()}, median: {group_counts.median()}, max: {group_counts.max()}")
else:
    print("No overlap.")
print("mean/std use train period only: No (z-score normalization currently uses the entire merged dataset before time-based split).")
