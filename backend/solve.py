import pandas as pd
import numpy as np
import pickle
import os
import sys

# 1. Diagnose near-zero map
print("1. Diagnose near-zero map")
era5 = pd.read_parquet('../model/datasets/era5_processed.parquet')
tigge = pd.read_parquet('../model/datasets/tigge_ncep_2023_2024.parquet')
if 'tp' in era5.columns:
    era5['tp'] = era5['tp'] * 1000.0
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)
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

merged = pd.merge(tigge_sub, era5_sub, on=['valid_time', 'latitude', 'longitude'], how='inner', suffixes=('_fcst', '_obs'))

# Compute busting (simplified for diagnosis)
merged['raw_err_tp'] = merged['precipitation'] - merged['tp']
merged['error_tp'] = np.abs(merged['raw_err_tp'])
merged['error_msl'] = np.abs(merged['mslp'] - merged['msl'])
merged['month'] = pd.to_datetime(merged['valid_time']).dt.month
feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'mslp', 'u10_fcst', 'v10_fcst', 'temperature_2m', 'precipitation']
X = merged[['valid_time', 'error_tp', 'error_msl'] + feature_cols].copy()
rename_dict = {'mslp': 'msl', 'u10_fcst': '10u', 'v10_fcst': '10v', 'temperature_2m': '2t', 'precipitation': 'tp'}
X = X.rename(columns=rename_dict).fillna(0)
X = X.sort_values('valid_time')
calib_idx = int(len(X) * 0.85)
train_data = X.iloc[:int(len(X)*0.7)]
test_data = X.iloc[calib_idx:]

final_feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
X_test = test_data[final_feature_cols]
X_train = train_data[final_feature_cols]

with open("../model/weights/calibrated_xgb.pkl", "rb") as f:
    calibrator = pickle.load(f)

# CalibratedClassifierCV doesn't have `predict_proba` for the raw base estimator easily if cv=3
# It fits 3 separate calibrators and estimators.
# I'll just print calibrated prob.
cal_probs = calibrator.predict_proba(X_test)[:, 1]
print(f"Mean predicted probability on held-out test split (calibrated): {np.mean(cal_probs):.4f}")

print("\nPer-feature mean and std (Training vs Live 2026-09-27):")
sys.path.append(".")
from app.feature_provider import get_forecast_features_batch
live_df, mode = get_forecast_features_batch("2026-09-27T00:00:00", 1)

for col in final_feature_cols:
    t_mean = X_train[col].mean()
    t_std = X_train[col].std()
    l_mean = live_df[col].mean() if col in live_df.columns else np.nan
    l_std = live_df[col].std() if col in live_df.columns else np.nan
    print(f"  {col}: Train (mean={t_mean:.2f}, std={t_std:.2f}) | Live (mean={l_mean:.2f}, std={l_std:.2f})")

# Determine shift or bug
# GFS SLP is in Pa. TIGGE MSLP is in Pa too? Let's check the numbers.
print("Distribution shift / Bug:")
# Will see from output.

print("\n3. Historical vs live map exactly matched")
print("The forecast_date '2023-10-15' was used for the historical map. This date is within the historical data range, so determine_routing_mode correctly routed it to 'historical'. The reason the stats matched live (mean=0.003, p90=0.006) is because both historical and live are fed through the same calibrated model, and if their input feature distributions have shifted or mean predictions are universally low, they will both collapse to similar near-zero values. Also, wait! If they are exactly identical, it might be returning climatology for both!")
