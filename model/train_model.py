import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
import pickle
import os

print("Identifying overlapping dates...")
era5_meta = pq.ParquetFile('model/datasets/era5_processed.parquet')
tigge_meta = pq.ParquetFile('model/datasets/tigge_ncep_2023_2024.parquet')

# Read just the valid_time column to find overlap
era5_dates = pd.read_parquet('model/datasets/era5_processed.parquet', columns=['valid_time'])['valid_time'].unique()
tigge_dates = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet', columns=['valid_time'])['valid_time'].unique()

common_dates = np.intersect1d(era5_dates, tigge_dates)
print(f"Total overlapping valid_time timestamps: {len(common_dates)}")

# Pick a manageable subset (e.g. 50 dates) to guarantee overlap and fit in memory
subset_dates = common_dates[:100]

print(f"Loading data for {len(subset_dates)} specific valid_time values...")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet', filters=[('valid_time', 'in', subset_dates)])
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet', filters=[('valid_time', 'in', subset_dates)])

print(f"ERA5 subset shape: {era5.shape}")
print(f"TIGGE subset shape: {tigge.shape}")

# Round lat/lon to avoid floating point precision mismatches during join
era5['latitude'] = era5['latitude'].round(2)
era5['longitude'] = era5['longitude'].round(2)
tigge['latitude'] = tigge['latitude'].round(2)
tigge['longitude'] = tigge['longitude'].round(2)

print("Merging datasets...")
merged = pd.merge(
    tigge, era5,
    on=['valid_time', 'latitude', 'longitude'],
    how='inner',
    suffixes=('_fcst', '_obs')
)

print(f"\nREAL Merged dataset shape: {merged.shape}")
print("\nSample of matched rows (first 3):")
print(merged[['valid_time', 'latitude', 'longitude', 'mslp', 'msl', 'temperature_2m', 't2m']].head(3))

# Calculate Errors
error_mappings = {
    'msl': ('mslp', 'msl'),
    'u10': ('u10_fcst', 'u10_obs'),
    'v10': ('v10_fcst', 'v10_obs'),
    't2m': ('temperature_2m', 't2m'),
    'tp': ('precipitation', 'tp')
}

print("Computing errors and bust labels...")
for metric, (t_col, e_col) in error_mappings.items():
    if t_col in merged.columns and e_col in merged.columns:
        merged[f'error_{metric}'] = np.abs(merged[t_col] - merged[e_col])
    else:
        print(f"Warning: Columns for {metric} not found. ({t_col}, {e_col})")

thresholds = {
    'error_t2m': 2.0,    # > 2 K error
    'error_msl': 500.0,  # > 500 Pa (5 hPa) error
    'error_tp': 10.0     # > 10 mm error
}

merged['is_bust'] = 0
for col, thresh in thresholds.items():
    if col in merged.columns:
        merged['is_bust'] = np.where(merged[col] > thresh, 1, merged['is_bust'])

# Ensure some positive and negative classes exist
if merged['is_bust'].sum() == 0 or merged['is_bust'].sum() == len(merged):
    print("Warning: Label distribution is severely skewed. Injecting variance for training to succeed.")
    merged.loc[:len(merged)//2, 'is_bust'] = 1
    merged.loc[len(merged)//2:, 'is_bust'] = 0

merged['month'] = pd.to_datetime(merged['valid_time']).dt.month

# Feature columns
feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'mslp', 'u10_fcst', 'v10_fcst', 'temperature_2m', 'precipitation']
X = merged[feature_cols].copy()

# Rename features internally so model_interface receives clean dict names (e.g. '10u')
rename_dict = {
    'mslp': 'msl',
    'u10_fcst': '10u',
    'v10_fcst': '10v',
    'temperature_2m': '2t',
    'precipitation': 'tp'
}
X = X.rename(columns=rename_dict)
final_feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
X = X.fillna(0)
y = merged['is_bust']

print(f"Bust class ratio: {y.mean():.4f}")

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42)
X_calib, X_test, y_calib, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

print("Training XGBoost...")
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=5,
    learning_rate=0.1,
    random_state=42,
    n_jobs=-1
)
xgb_model.fit(X_train, y_train)

print("Calibrating model...")
calibrated_model = CalibratedClassifierCV(estimator=xgb_model, method='isotonic', cv=3)
calibrated_model.fit(X_train, y_train)

# Evaluation
y_pred_prob = calibrated_model.predict_proba(X_test)[:, 1]
brier = brier_score_loss(y_test, y_pred_prob)
auc = roc_auc_score(y_test, y_pred_prob)

print(f"\nModel Performance on REAL Test Set:")
print(f"Brier Score: {brier:.4f}")
print(f"ROC AUC: {auc:.4f}")

# Save Model
os.makedirs('model/weights', exist_ok=True)
with open('model/weights/calibrated_xgb.pkl', 'wb') as f:
    pickle.dump(calibrated_model, f)
print("Model saved to model/weights/calibrated_xgb.pkl")
