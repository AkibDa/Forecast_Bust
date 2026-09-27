import pandas as pd
import numpy as np
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

from sklearn.metrics import brier_score_loss, roc_auc_score, confusion_matrix, precision_score, recall_score
# ...
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
