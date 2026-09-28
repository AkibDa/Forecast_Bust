import pandas as pd
import numpy as np

print("\n--- 3. Normalization ---")
print("Simulating normalization logic on the train split.")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'tp' in era5.columns:
    era5['tp'] = era5['tp'] * 1000.0
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation'])
tigge['precip_24h'] = tigge['precip_24h'].clip(lower=0)
tigge['precipitation'] = tigge['precip_24h']

common_dates = np.intersect1d(era5['valid_time'].unique(), tigge['valid_time'].unique())
common_dates = np.sort(common_dates)
if len(common_dates) > 300:
    indices = np.linspace(0, len(common_dates) - 1, 300, dtype=int)
    subset_dates = common_dates[indices]
else:
    subset_dates = common_dates

era5_sub = era5[era5['valid_time'].isin(subset_dates)].copy()
tigge_sub = tigge[tigge['valid_time'].isin(subset_dates)].copy()

era5_sub['latitude'] = era5_sub['latitude'].round(2)
era5_sub['longitude'] = era5_sub['longitude'].round(2)
tigge_sub['latitude'] = tigge_sub['latitude'].round(2)
tigge_sub['longitude'] = tigge_sub['longitude'].round(2)

merged = pd.merge(
    tigge_sub, era5_sub,
    on=['valid_time', 'latitude', 'longitude'],
    how='inner',
    suffixes=('_fcst', '_obs')
)

merged['raw_err_tp'] = merged['precipitation'] - merged['tp']
merged['raw_err_t2m'] = merged['temperature_2m'] - merged['t2m']
merged['raw_err_msl'] = merged['mslp'] - merged['msl']
merged['error_tp'] = np.abs(merged['raw_err_tp'])

# Create time splits
merged = merged.sort_values('valid_time')
n_total = len(merged)
train_idx = int(n_total * 0.7)
calib_idx = int(n_total * 0.85)

train_df = merged.iloc[:train_idx]
calib_df = merged.iloc[train_idx:calib_idx]
test_df = merged.iloc[calib_idx:]

group_cols = ['latitude', 'longitude', 'lead_time_hours']
stats = train_df.groupby(group_cols)[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std']).reset_index()
stats.columns = group_cols + [
    'mean_err_t2m', 'std_err_t2m',
    'mean_err_msl', 'std_err_msl',
    'mean_err_tp',  'std_err_tp'
]
train_df = pd.merge(train_df, stats, on=group_cols, how='left')

train_df['z_t2m'] = np.abs(train_df['raw_err_t2m'] - train_df['mean_err_t2m']) / (train_df['std_err_t2m'] + 1e-6)
train_df['z_msl'] = np.abs(train_df['raw_err_msl'] - train_df['mean_err_msl']) / (train_df['std_err_msl'] + 1e-6)
train_df['z_tp']  = np.abs(train_df['raw_err_tp'] - train_df['mean_err_tp']) / (train_df['std_err_tp'] + 1e-6)
train_df['max_z'] = train_df[['z_t2m', 'z_msl', 'z_tp']].max(axis=1)

q90 = train_df.groupby('lead_time_hours')['max_z'].quantile(0.90).reset_index(name='q90_z')
train_df = pd.merge(train_df, q90, on='lead_time_hours', how='left')
train_df['is_bust'] = (train_df['max_z'] > train_df['q90_z']).astype(int)

# Group size distribution
group_sizes = train_df.groupby(['latitude', 'longitude', 'lead_time_hours']).size()
print("Group size distribution (training period only):")
print(group_sizes.describe())
print(f"New base rate (simulated with train-only stats): {train_df['is_bust'].mean():.4f}")


print("\n--- 4. Real train vs live feature statistics ---")
import sys
import os
os.environ['ALLOW_CLIMATOLOGY_FALLBACK'] = 'true'
sys.path.append('backend')
from app.feature_provider import get_forecast_features_batch

# Load training features for descriptive stats
expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
train_features = train_df.rename(columns={'mslp': 'msl', 'u10_fcst': '10u', 'v10_fcst': '10v', 'temperature_2m': '2t', 'precipitation': 'tp'})
train_features['month'] = pd.to_datetime(train_features['valid_time']).dt.month
print("Training feature statistics (df.describe()):")
print(train_features[expected_cols].describe().to_string())

# Load Live features for 2026-09-27 lead 1
print("\nLive feature statistics (2026-09-27 lead 1):")
live_df, mode = get_forecast_features_batch('2026-09-27', 1)
print(live_df[expected_cols].describe().to_string())

# Predict with month set to training value
from app.model_interface import predict_batch, _load_model
_load_model()
live_df_mod = live_df.copy()
# Set month to a mean training value, e.g., 6
live_df_mod['month'] = 6
preds = predict_batch(live_df_mod)
mean_prob = preds['bust_probability'].mean()
print(f"\nMean predicted probability for the live day when month is set to 6: {mean_prob:.4f}")

print("\n--- 5. True training-set base rate & distinct init dates ---")
# True base rate from the current implementation is based on all data
all_stats = merged.groupby(group_cols)[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std']).reset_index()
all_stats.columns = group_cols + [
    'mean_err_t2m', 'std_err_t2m',
    'mean_err_msl', 'std_err_msl',
    'mean_err_tp',  'std_err_tp'
]
merged_base = pd.merge(merged, all_stats, on=group_cols, how='left')
merged_base['z_t2m'] = np.abs(merged_base['raw_err_t2m'] - merged_base['mean_err_t2m']) / (merged_base['std_err_t2m'] + 1e-6)
merged_base['z_msl'] = np.abs(merged_base['raw_err_msl'] - merged_base['mean_err_msl']) / (merged_base['std_err_msl'] + 1e-6)
merged_base['z_tp']  = np.abs(merged_base['raw_err_tp'] - merged_base['mean_err_tp']) / (merged_base['std_err_tp'] + 1e-6)
merged_base['max_z'] = merged_base[['z_t2m', 'z_msl', 'z_tp']].max(axis=1)
q90_all = merged_base.groupby('lead_time_hours')['max_z'].quantile(0.90).reset_index(name='q90_z')
merged_base = pd.merge(merged_base, q90_all, on='lead_time_hours', how='left')
merged_base['is_bust'] = (merged_base['max_z'] > merged_base['q90_z']).astype(int)

train_base_df = merged_base.iloc[:train_idx]
print(f"True training-set base rate (using current normalization across all data): {train_base_df['is_bust'].mean():.4f}")

train_inits = len(train_df['init_time'].dt.date.unique())
calib_inits = len(calib_df['init_time'].dt.date.unique())
test_inits = len(test_df['init_time'].dt.date.unique())
print(f"Distinct init dates -> Train: {train_inits}, Calib: {calib_inits}, Test: {test_inits}")
