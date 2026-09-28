import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import brier_score_loss, roc_auc_score
import os

print("\n--- 1. ACCUMULATION CHECK ---")
era5 = pd.read_parquet('../model/datasets/era5_processed.parquet')
tigge = pd.read_parquet('../model/datasets/tigge_ncep_2023_2024.parquet')

if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

sample_init = tigge['init_time'].iloc[0]
sample_lat = tigge['latitude'].iloc[0]
sample_lon = tigge['longitude'].iloc[0]

tigge_sample = tigge[(tigge['init_time'] == sample_init) & 
                     (tigge['latitude'] == sample_lat) & 
                     (tigge['longitude'] == sample_lon)].sort_values('lead_time_hours')

print(f"Sample cell: lat={sample_lat}, lon={sample_lon}, init_time={sample_init}")
print("TIGGE tp across lead times:")
print(tigge_sample[['lead_time_hours', 'precipitation']].to_string(index=False))

era5_sample = era5[(era5['latitude'] == sample_lat) & (era5['longitude'] == sample_lon) & 
                   (era5['valid_time'].isin(tigge_sample['valid_time']))].sort_values('valid_time')
print("\nERA5 tp for corresponding valid_times:")
print(era5_sample[['valid_time', 'tp']].to_string(index=False))

print("\n--- 2. LABEL DIAGNOSTICS ---")
# Use the merged dataframe logic from train_model.py
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

merged = pd.merge(tigge_sub, era5_sub, on=['valid_time', 'latitude', 'longitude'], how='inner', suffixes=('_fcst', '_obs'))

merged['error_t2m'] = np.abs(merged['temperature_2m'] - merged['t2m'])
merged['error_msl'] = np.abs(merged['mslp'] - merged['msl'])
merged['error_tp'] = np.abs(merged['precipitation'] - merged['tp'])

merged['bust_t2m'] = merged['error_t2m'] > 2.0
merged['bust_msl'] = merged['error_msl'] > 500.0
merged['bust_tp'] = merged['error_tp'] > 10.0
merged['is_bust'] = (merged['bust_t2m'] | merged['bust_msl'] | merged['bust_tp']).astype(int)

print(f"Overall Bust Rate: {merged['is_bust'].mean():.4f}")
print("\nBust Rate by lead_time_hours:")
print(merged.groupby('lead_time_hours')['is_bust'].mean())

print("\nBust Rate by Condition (T2M, MSL, TP):")
print(f"T2M (>2K): {merged['bust_t2m'].mean():.4f}")
print(f"MSL (>500Pa): {merged['bust_msl'].mean():.4f}")
print(f"TP (>10mm): {merged['bust_tp'].mean():.4f}")

print("\nOverlap combinations:")
print(merged.groupby(['bust_t2m', 'bust_msl', 'bust_tp']).size() / len(merged))

merged['lat_band'] = pd.cut(merged['latitude'], bins=[0, 20, 28, 90], labels=['low', 'mid', 'high (terrain)'])
print("\nBust Rate by Latitude Band:")
print(merged.groupby('lat_band', observed=False)['is_bust'].mean())

print("\nTop 10 largest TP errors (init_time, valid_time, error):")
top_tp = merged.nlargest(10, 'error_tp')[['init_time', 'valid_time', 'latitude', 'longitude', 'precipitation', 'tp', 'error_tp']]
print(top_tp)

print("\n--- 3. BASELINES ---")
X = merged.copy().sort_values('valid_time')
n_total = len(X)
train_idx = int(n_total * 0.7)
calib_idx = int(n_total * 0.85)

train_data = X.iloc[:train_idx]
test_data = X.iloc[calib_idx:]

y_train = train_data['is_bust']
y_test = test_data['is_bust']

# Baseline A: lead_time_hours only
X_train_a = train_data[['lead_time_hours']]
X_test_a = test_data[['lead_time_hours']]
model_a = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, n_jobs=-1)
model_a.fit(X_train_a, y_train)
pred_a = model_a.predict_proba(X_test_a)[:, 1]
print(f"Baseline A (lead_time only) - AUC: {roc_auc_score(y_test, pred_a):.4f}, Brier: {brier_score_loss(y_test, pred_a):.4f}")

# Baseline B: lead_time + lat + lon
X_train_b = train_data[['lead_time_hours', 'latitude', 'longitude']]
X_test_b = test_data[['lead_time_hours', 'latitude', 'longitude']]
model_b = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1)
model_b.fit(X_train_b, y_train)
pred_b = model_b.predict_proba(X_test_b)[:, 1]
print(f"Baseline B (lead_time+lat+lon) - AUC: {roc_auc_score(y_test, pred_b):.4f}, Brier: {brier_score_loss(y_test, pred_b):.4f}")
