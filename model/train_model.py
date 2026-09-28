import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
import pickle
import os

print("Identifying overlapping dates...")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')

# Convert ERA5 tp from meters to mm
if 'tp' in era5.columns:
    era5['tp'] = era5['tp'] * 1000.0

# Convert TIGGE tp from accumulated to 24h differenced
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation'])
# Ensure no negative precip from bad differencing
tigge['precip_24h'] = tigge['precip_24h'].clip(lower=0)
tigge['precipitation'] = tigge['precip_24h']

common_dates = np.intersect1d(era5['valid_time'].unique(), tigge['valid_time'].unique())
common_dates = np.sort(common_dates)
print(f"Total overlapping valid_time timestamps: {len(common_dates)}")

if len(common_dates) > 300:
    indices = np.linspace(0, len(common_dates) - 1, 300, dtype=int)
    subset_dates = common_dates[indices]
else:
    subset_dates = common_dates

print(f"Loading data for {len(subset_dates)} specific valid_time values...")
era5_sub = era5[era5['valid_time'].isin(subset_dates)].copy()
tigge_sub = tigge[tigge['valid_time'].isin(subset_dates)].copy()

era5_sub['latitude'] = era5_sub['latitude'].round(2)
era5_sub['longitude'] = era5_sub['longitude'].round(2)
tigge_sub['latitude'] = tigge_sub['latitude'].round(2)
tigge_sub['longitude'] = tigge_sub['longitude'].round(2)

print("Merging datasets...")
merged = pd.merge(
    tigge_sub, era5_sub,
    on=['valid_time', 'latitude', 'longitude'],
    how='inner',
    suffixes=('_fcst', '_obs')
)

print(f"REAL Merged dataset shape: {merged.shape}")

print("Computing bias-corrected errors and bust labels...")
merged['raw_err_t2m'] = merged['temperature_2m'] - merged['t2m']
merged['raw_err_msl'] = merged['mslp'] - merged['msl']
merged['raw_err_tp'] = merged['precipitation'] - merged['tp']

group_cols = ['latitude', 'longitude', 'lead_time_hours']
stats = merged.groupby(group_cols)[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std']).reset_index()
stats.columns = group_cols + [
    'mean_err_t2m', 'std_err_t2m',
    'mean_err_msl', 'std_err_msl',
    'mean_err_tp',  'std_err_tp'
]

merged = pd.merge(merged, stats, on=group_cols, how='left')

# Normalized absolute errors (z-scores)
merged['z_t2m'] = np.abs(merged['raw_err_t2m'] - merged['mean_err_t2m']) / (merged['std_err_t2m'] + 1e-6)
merged['z_msl'] = np.abs(merged['raw_err_msl'] - merged['mean_err_msl']) / (merged['std_err_msl'] + 1e-6)
merged['z_tp']  = np.abs(merged['raw_err_tp'] - merged['mean_err_tp']) / (merged['std_err_tp'] + 1e-6)

# Top 10% bust definition across any variable
merged['max_z'] = merged[['z_t2m', 'z_msl', 'z_tp']].max(axis=1)
q90 = merged.groupby('lead_time_hours')['max_z'].quantile(0.90).reset_index(name='q90_z')
merged = pd.merge(merged, q90, on='lead_time_hours', how='left')

merged['is_bust'] = (merged['max_z'] > merged['q90_z']).astype(int)
# Store absolute tp error for the backtest display
merged['error_tp'] = np.abs(merged['raw_err_tp'])
merged['error_msl'] = np.abs(merged['raw_err_msl'])

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../backend'))
from app.shared_utils import get_month_from_dates

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

# BASELINE EVALUATIONS
print("\n--- BASELINES ---")
X_train_a = X_train[['lead_time_hours']]
X_test_a = X_test[['lead_time_hours']]
model_a = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, n_jobs=-1)
model_a.fit(X_train_a, y_train)
pred_a = model_a.predict_proba(X_test_a)[:, 1]
brier_a = brier_score_loss(y_test, pred_a)
auc_a = roc_auc_score(y_test, pred_a)
print(f"Baseline A (lead_time only) - AUC: {auc_a:.4f}, Brier: {brier_a:.4f}")

print("\n--- FULL MODEL ---")
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

from sklearn.metrics import brier_score_loss, roc_auc_score, confusion_matrix, precision_score, recall_score
y_pred_prob = calibrated_model.predict_proba(X_test)[:, 1]
y_pred = (y_pred_prob > 0.5).astype(int)

brier = brier_score_loss(y_test, y_pred_prob)
auc = roc_auc_score(y_test, y_pred_prob)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
cm = confusion_matrix(y_test, y_pred)

print(f"\nModel Performance on TIME-BASED Test Set:")
print(f"Brier Score: {brier:.4f}")
print(f"ROC AUC: {auc:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"Confusion Matrix:\n{cm}")

gain_auc = auc - auc_a
print(f"\nGain over Baseline A (AUC): +{gain_auc:.4f}")

os.makedirs('model/weights', exist_ok=True)
with open('model/weights/calibrated_xgb.pkl', 'wb') as f:
    pickle.dump(calibrated_model, f)
print("Model saved to model/weights/calibrated_xgb.pkl")

# --- BACKTEST EXTREME EVENTS ---
print("\n--- Backtesting Extreme Events in Test Set ---")
test_data = test_data.copy()
test_data['predicted_bust_prob'] = y_pred_prob
test_data['confidence_score'] = 1.0 - y_pred_prob

# Find the extreme precipitation busts in the test set
extreme_candidates = test_data[test_data['is_bust'] == 1].sort_values('error_tp', ascending=False)

selected_events = []
for idx, row in extreme_candidates.iterrows():
    if len(selected_events) >= 3:
        break
        
    date_str = str(row['valid_time']).split(' ')[0]
    lat = row['latitude']
    lon = row['longitude']
    
    # Check if this candidate is sufficiently independent from already selected events
    is_independent = True
    for ev in selected_events:
        dist = np.sqrt((ev['lat'] - lat)**2 + (ev['lon'] - lon)**2)
        if ev['date'] == date_str or dist < 2.0:
            is_independent = False
            break
            
    if is_independent:
        selected_events.append({
            'date': date_str,
            'lat': lat,
            'lon': lon,
            'error': row['error_tp'],
            'prob': row['predicted_bust_prob'],
            'conf': row['confidence_score']
        })

print("Top 3 INDEPENDENT Heavy Rainfall/Extreme Error Cases:")
for ev in selected_events:
    print(f"\nEvent Date: {ev['date']}, Location: ({ev['lat']:.2f}, {ev['lon']:.2f})")
    print(f"Observed error in precipitation (tp): {ev['error']:.2f} mm")
    print(f"Predicted Bust Probability: {ev['prob']:.4f}")
    print(f"Confidence Score: {ev['conf']:.4f}")
