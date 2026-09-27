import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
import pickle
import os

print("Identifying overlapping dates...")
era5_dates = pd.read_parquet('model/datasets/era5_processed.parquet', columns=['valid_time'])['valid_time'].unique()
tigge_dates = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet', columns=['valid_time'])['valid_time'].unique()

common_dates = np.intersect1d(era5_dates, tigge_dates)
common_dates = np.sort(common_dates)
print(f"Total overlapping valid_time timestamps: {len(common_dates)}")

# Scale up: pick ~300 dates evenly spaced to cover different seasons/months
if len(common_dates) > 300:
    indices = np.linspace(0, len(common_dates) - 1, 300, dtype=int)
    subset_dates = common_dates[indices]
else:
    subset_dates = common_dates

print(f"Loading data for {len(subset_dates)} specific valid_time values...")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet', filters=[('valid_time', 'in', subset_dates)])
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet', filters=[('valid_time', 'in', subset_dates)])

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

print(f"REAL Merged dataset shape: {merged.shape}")

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

thresholds = {
    'error_t2m': 2.0,    # > 2 K error
    'error_msl': 500.0,  # > 500 Pa (5 hPa) error
    'error_tp': 10.0     # > 10 mm error
}

merged['is_bust'] = 0
for col, thresh in thresholds.items():
    if col in merged.columns:
        merged['is_bust'] = np.where(merged[col] > thresh, 1, merged['is_bust'])

merged['month'] = pd.to_datetime(merged['valid_time']).dt.month

feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'mslp', 'u10_fcst', 'v10_fcst', 'temperature_2m', 'precipitation']
X = merged[['valid_time', 'is_bust', 'error_tp', 'error_msl'] + feature_cols].copy()

# Rename features internally
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

# --- TIME-BASED SPLIT ---
print("Performing time-based train/test split...")
X = X.sort_values('valid_time')

n_total = len(X)
train_idx = int(n_total * 0.7)
calib_idx = int(n_total * 0.85)

train_data = X.iloc[:train_idx]
calib_data = X.iloc[train_idx:calib_idx]
test_data = X.iloc[calib_idx:]

X_train = train_data[final_feature_cols]
y_train = train_data['is_bust']

X_calib = calib_data[final_feature_cols]
y_calib = calib_data['is_bust']

X_test = test_data[final_feature_cols]
y_test = test_data['is_bust']

print(f"Train samples: {len(X_train)}, Calib samples: {len(X_calib)}, Test samples: {len(X_test)}")
print(f"Test Set Bust Ratio: {y_test.mean():.4f}")

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

print(f"\nModel Performance on TIME-BASED Test Set:")
print(f"Brier Score: {brier:.4f}")
print(f"ROC AUC: {auc:.4f}")

os.makedirs('model/weights', exist_ok=True)
with open('model/weights/calibrated_xgb.pkl', 'wb') as f:
    pickle.dump(calibrated_model, f)
print("Model saved to model/weights/calibrated_xgb.pkl")

# --- BACKTEST EXTREME EVENTS ---
print("\n--- Backtesting Extreme Events in Test Set ---")
test_data['predicted_bust_prob'] = y_pred_prob
test_data['confidence_score'] = 1.0 - y_pred_prob

# Find the top 3 extreme precipitation busts in the test set
extreme_precip_cases = test_data[test_data['is_bust'] == 1].sort_values('error_tp', ascending=False).head(3)

print("Top 3 Heavy Rainfall/Extreme Error Cases Discovered in Data:")
for idx, row in extreme_precip_cases.iterrows():
    date_str = str(row['valid_time']).split(' ')[0]
    print(f"\nEvent Date: {date_str}, Location: ({row['latitude']:.2f}, {row['longitude']:.2f})")
    print(f"Observed error in precipitation (tp): {row['error_tp']:.2f} mm")
    print(f"Predicted Bust Probability: {row['predicted_bust_prob']:.4f}")
    print(f"Confidence Score: {row['confidence_score']:.4f}")
