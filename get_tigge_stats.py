import pandas as pd
import numpy as np

# Load tigge
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

init_times = np.sort(tigge['init_time'].unique())
distinct_inits = len(init_times)

diffs = pd.Series(init_times).diff().dropna().dt.total_seconds() / 86400.0

if len(diffs) > 0:
    min_diff, med_diff, max_diff = diffs.min(), diffs.median(), diffs.max()
else:
    min_diff, med_diff, max_diff = 0, 0, 0

print(f"Number of distinct TIGGE init_times: {distinct_inits}")
print(f"Gaps between consecutive init_times (days) - min: {min_diff}, median: {med_diff}, max: {max_diff}")

# Number of init dates in the merged training set
era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
common_dates = np.intersect1d(era5['valid_time'].unique(), tigge['valid_time'].unique())
common_dates = np.sort(common_dates)
if len(common_dates) > 300:
    indices = np.linspace(0, len(common_dates) - 1, 300, dtype=int)
    subset_dates = common_dates[indices]
else:
    subset_dates = common_dates

tigge_sub = tigge[tigge['valid_time'].isin(subset_dates)].copy()
merged_init_dates = len(tigge_sub['init_time'].dt.date.unique())
print(f"Number of init dates in the merged training set: {merged_init_dates}")
