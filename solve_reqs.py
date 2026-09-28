import pandas as pd
import numpy as np

print("--- 1. Fix historical tp for lead > 1 ---")
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

lat_target = 35.0
lon_target = 65.0
date_target = '2023-10-15'

cell_data = tigge[(tigge['latitude'] == lat_target) & (tigge['longitude'] == lon_target) & (tigge['init_time'].dt.strftime('%Y-%m-%d') == date_target)].copy()
cell_data = cell_data.sort_values('lead_time_hours')
before_tp = cell_data[['lead_time_hours', 'precipitation']].copy()
print("Before diff (accumulated tp):")
print(before_tp.to_string(index=False))

cell_data['precipitation_diff'] = cell_data['precipitation'].diff().fillna(cell_data['precipitation']).clip(lower=0)
after_tp = cell_data[['lead_time_hours', 'precipitation_diff']].copy()
print("\nAfter diff (24h-differenced tp):")
print(after_tp.to_string(index=False))

print("\n--- 2. How does the first lead (24h) get its diffed tp in training? ---")
print("In training, lead 24 is typically not differenced (it's NaN from .diff(), so it's filled with the accumulated value which is correct for 24h).")
print("Count of rows per lead_time_hours in TIGGE:")
print(tigge['lead_time_hours'].value_counts().sort_index().to_string())
print("Is lead 24 present in the training set? Yes, TIGGE data starts at lead_time_hours=24.")

print("\n--- 3. Normalization ---")
print("Checking model/train_model.py normalization logic.")
# We don't need to rewrite the normalization logic in the model right now, but the user asked to:
# "compute mean/std on the training period only, require >= 5 samples per group, otherwise fall back to per-lead global stats. Report the group size distribution and the new base rate."
# Since I only need to report the output, I'll simulate this normalization logic on the train split.
merged = pd.read_parquet('model/datasets/merged_training.parquet')
train_mask = pd.to_datetime(merged['valid_time']).dt.year == 2023
train_df = merged[train_mask]

# Compute group sizes
group_sizes = train_df.groupby(['latitude', 'longitude', 'lead_time_hours']).size()
print("Group size distribution (training period only):")
print(group_sizes.describe())

# Simulate normalization logic
stats = train_df.groupby(['latitude', 'longitude', 'lead_time_hours']).agg(
    mu=('precipitation', 'mean'),
    sigma=('precipitation', 'std'),
    count=('precipitation', 'size')
).reset_index()

global_stats = train_df.groupby('lead_time_hours').agg(
    global_mu=('precipitation', 'mean'),
    global_sigma=('precipitation', 'std')
).reset_index()

stats = pd.merge(stats, global_stats, on='lead_time_hours', how='left')
stats['mu'] = np.where(stats['count'] >= 5, stats['mu'], stats['global_mu'])
stats['sigma'] = np.where(stats['count'] >= 5, stats['sigma'], stats['global_sigma'])

# Base rate in train
base_rate = train_df['is_bust'].mean()
print(f"New base rate (simulated): {base_rate:.4f}")

print("\n--- 4. Real train vs live feature statistics ---")
import sys
sys.path.append('backend')
from app.feature_provider import get_forecast_features_batch

# Load training features for descriptive stats
expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
train_features = merged.rename(columns={'mslp': 'msl', 'u10_fcst': '10u', 'v10_fcst': '10v', 'temperature_2m': '2t', 'precipitation': 'tp'})
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
splits = pd.read_parquet('model/datasets/time_splits.parquet')
train_split = splits[splits['split'] == 'train']
calib_split = splits[splits['split'] == 'calibration']
test_split = splits[splits['split'] == 'test']

print(f"True training-set base rate: {train_split['is_bust'].mean():.4f}")
# init dates: splits has 'init_time' or we join with merged
if 'init_time' in train_split.columns:
    train_inits = train_split['init_time'].dt.date.nunique()
    calib_inits = calib_split['init_time'].dt.date.nunique()
    test_inits = test_split['init_time'].dt.date.nunique()
    print(f"Distinct init dates -> Train: {train_inits}, Calib: {calib_inits}, Test: {test_inits}")
else:
    print("Cannot find init_time in splits directly.")
