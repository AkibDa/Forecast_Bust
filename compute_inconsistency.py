import pandas as pd
import numpy as np
from scipy.stats import pearsonr

print("Loading data...")
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

# We want pairs of forecasts valid at the same time but from different runs (init_time).
# Since TIGGE init spacing is 1 day, for a valid_time, we have forecasts from multiple init_times.
# Let's define inconsistency as the difference between the Day 2 forecast (lead_time_hours=48)
# and the Day 1 forecast (lead_time_hours=24) for the SAME valid_time.

print("Computing run-to-run inconsistency...")
# Let's extract tp (precip_24h)
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)

df_d1 = tigge[tigge['lead_time_hours'] == 24].copy()
df_d2 = tigge[tigge['lead_time_hours'] == 48].copy()

# Merge on valid_time and location
merged_runs = pd.merge(df_d1, df_d2, on=['latitude', 'longitude', 'valid_time'], suffixes=('_d1', '_d2'))

merged_runs['month'] = merged_runs['valid_time'].dt.month
merged_runs['inconsistency_tp'] = np.abs(merged_runs['precip_24h_d1'] - merged_runs['precip_24h_d2'])

pairs_per_month = merged_runs.groupby('month').size()
print("\nNumber of pairs per month:")
print(pairs_per_month.to_string())

# Correlation with actual ERA5 error on the 10 overlap days
print("\nLoading ERA5 for correlation on overlap days...")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
if 'tp' in era5.columns:
    era5['tp'] = era5['tp'] * 1000.0

common_dates = np.intersect1d(era5['valid_time'].unique(), merged_runs['valid_time'].unique())

if len(common_dates) > 0:
    era5_sub = era5[era5['valid_time'].isin(common_dates)]
    merged_runs_sub = merged_runs[merged_runs['valid_time'].isin(common_dates)]
    
    # Merge with ERA5
    eval_df = pd.merge(merged_runs_sub, era5_sub, on=['valid_time', 'latitude', 'longitude'])
    eval_df['actual_error_tp'] = np.abs(eval_df['precip_24h_d1'] - eval_df['tp']) # error of the day 1 forecast
    
    corr, pval = pearsonr(eval_df['inconsistency_tp'], eval_df['actual_error_tp'])
    print(f"\nCorrelation between run-to-run inconsistency and actual ERA5 error (on {len(common_dates)} overlap days): {corr:.4f} (p-value: {pval:.4f})")
else:
    print("\nNo overlap dates found for correlation.")
