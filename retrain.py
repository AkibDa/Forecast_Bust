import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
import pickle
import os
import gc

print("Loading TIGGE data...")
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

# Thin cells to avoid OOM: pick a 2-degree grid
lats = np.arange(5, 36, 2.0)
lons = np.arange(65, 101, 2.0)
tigge = tigge[(tigge['latitude'].isin(lats)) & (tigge['longitude'].isin(lons))].copy()

# Compute 24h differenced tp
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)

# Plan B: Proxy Label (since ERA5 is missing)
# Use lead 24 as the truth for tp, t2m, mslp
print("Computing proxy truth (lead 24)...")
truth = tigge[tigge['lead_time_hours'] == 24][['valid_time', 'latitude', 'longitude', 'precip_24h', 'temperature_2m', 'mslp']].copy()
truth = truth.rename(columns={'precip_24h': 'true_tp', 'temperature_2m': 'true_t2m', 'mslp': 'true_msl'})

# We can only evaluate forecasts for lead > 24 against the proxy truth
merged = pd.merge(tigge[tigge['lead_time_hours'] > 24], truth, on=['valid_time', 'latitude', 'longitude'], how='inner')

merged['raw_err_tp'] = merged['precip_24h'] - merged['true_tp']
merged['raw_err_t2m'] = merged['temperature_2m'] - merged['true_t2m']
merged['raw_err_msl'] = merged['mslp'] - merged['true_msl']

# Splits
merged['valid_date'] = pd.to_datetime(merged['valid_time']).dt.date
train_mask = merged['valid_date'] <= pd.to_datetime('2023-12-31').date()
calib_mask = (merged['valid_date'] >= pd.to_datetime('2024-01-10').date()) & (merged['valid_date'] <= pd.to_datetime('2024-06-30').date())
test_mask = (merged['valid_date'] >= pd.to_datetime('2024-07-10').date()) & (merged['valid_date'] <= pd.to_datetime('2024-12-31').date())

train_df = merged[train_mask].copy()

# Z-score stats from training period only, per (cell, lead)
print("Computing normalization stats on training split...")
group_cols = ['latitude', 'longitude', 'lead_time_hours']
stats = train_df.groupby(group_cols)[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std', 'size']).reset_index()
stats.columns = group_cols + [
    'mean_t2m', 'std_t2m', 'size_t2m',
    'mean_msl', 'std_msl', 'size_msl',
    'mean_tp', 'std_tp', 'size_tp'
]

# Fallback stats per lead
global_stats = train_df.groupby('lead_time_hours')[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std']).reset_index()
global_stats.columns = ['lead_time_hours', 'gmean_t2m', 'gstd_t2m', 'gmean_msl', 'gstd_msl', 'gmean_tp', 'gstd_tp']

stats = pd.merge(stats, global_stats, on='lead_time_hours', how='left')
for v in ['t2m', 'msl', 'tp']:
    stats[f'mean_{v}'] = np.where(stats[f'size_{v}'] >= 20, stats[f'mean_{v}'], stats[f'gmean_{v}'])
    stats[f'std_{v}'] = np.where(stats[f'size_{v}'] >= 20, stats[f'std_{v}'], stats[f'gstd_{v}'])

merged = pd.merge(merged, stats, on=group_cols, how='left')
merged['z_t2m'] = np.abs(merged['raw_err_t2m'] - merged['mean_t2m']) / (merged['std_t2m'] + 1e-6)
merged['z_msl'] = np.abs(merged['raw_err_msl'] - merged['mean_msl']) / (merged['std_msl'] + 1e-6)
merged['z_tp'] = np.abs(merged['raw_err_tp'] - merged['mean_tp']) / (merged['std_tp'] + 1e-6)
merged['max_z'] = merged[['z_t2m', 'z_msl', 'z_tp']].max(axis=1)

q90 = merged[train_mask].groupby('lead_time_hours')['max_z'].quantile(0.90).reset_index(name='q90_z')
merged = pd.merge(merged, q90, on='lead_time_hours', how='left')
merged['is_bust'] = (merged['max_z'] > merged['q90_z']).astype(int)
merged['month'] = pd.to_datetime(merged['valid_time']).dt.month

rename_dict = {'mslp': 'msl', 'u10': '10u', 'v10': '10v', 'temperature_2m': '2t', 'precip_24h': 'tp'}
merged = merged.rename(columns=rename_dict)
final_feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
merged[final_feature_cols] = merged[final_feature_cols].fillna(0)

# Final Splits
train_data = merged[merged['valid_date'] <= pd.to_datetime('2023-12-31').date()]
calib_data = merged[(merged['valid_date'] >= pd.to_datetime('2024-01-10').date()) & (merged['valid_date'] <= pd.to_datetime('2024-06-30').date())]
test_data = merged[(merged['valid_date'] >= pd.to_datetime('2024-07-10').date()) & (merged['valid_date'] <= pd.to_datetime('2024-12-31').date())]

print(f"\nBase rates - Train: {train_data['is_bust'].mean():.4f}, Calib: {calib_data['is_bust'].mean():.4f}, Test: {test_data['is_bust'].mean():.4f}")

# Train
X_train, y_train = train_data[final_feature_cols], train_data['is_bust']
X_calib, y_calib = calib_data[final_feature_cols], calib_data['is_bust']
X_test, y_test = test_data[final_feature_cols], test_data['is_bust']

print("Training baseline...")
base_cols = ['lead_time_hours', 'latitude', 'longitude', 'month']
xgb_base = xgb.XGBClassifier(n_estimators=50, max_depth=3, n_jobs=-1, random_state=42)
xgb_base.fit(X_train[base_cols], y_train)
base_preds = xgb_base.predict_proba(X_test[base_cols])[:, 1]
print(f"Baseline AUC: {roc_auc_score(y_test, base_preds):.4f}")

print("Training full model...")
xgb_model = xgb.XGBClassifier(n_estimators=50, max_depth=5, n_jobs=-1, random_state=42)
xgb_model.fit(X_train, y_train)

print("Calibrating...")
calibrated_model = CalibratedClassifierCV(estimator=xgb_model, method='isotonic', cv=3)
calibrated_model.fit(X_calib, y_calib)

y_pred_prob = calibrated_model.predict_proba(X_test)[:, 1]
print(f"Full Model AUC: {roc_auc_score(y_test, y_pred_prob):.4f}")
print(f"Full Model Brier Score: {brier_score_loss(y_test, y_pred_prob):.4f}")

# Reliability table
test_data['pred'] = y_pred_prob
test_data['bin'] = pd.qcut(test_data['pred'], q=10, duplicates='drop')
rel = test_data.groupby('bin').agg(mean_pred=('pred', 'mean'), actual_rate=('is_bust', 'mean'), count=('pred', 'size')).reset_index()
print("\n10-bin Reliability Table:")
print(rel.to_string())

print("\nPer-month AUC on Test Set:")
for m in test_data['month'].unique():
    subset = test_data[test_data['month'] == m]
    if len(subset['is_bust'].unique()) > 1:
        print(f"Month {m}: {roc_auc_score(subset['is_bust'], subset['pred']):.4f}")

sept_data = test_data[test_data['month'] == 9]
print(f"\nMean predicted probability on a September day: {sept_data['pred'].mean():.4f}")

os.makedirs('model/weights', exist_ok=True)
with open('model/weights/retrain_proxy_xgb.pkl', 'wb') as f:
    pickle.dump(calibrated_model, f)
print("\nModel saved to model/weights/retrain_proxy_xgb.pkl")
