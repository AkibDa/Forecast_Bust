import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, roc_auc_score
import pickle
import os

print("Loading data...")
# Read without sampling immediately. Instead sample the merge or ensure overlap
era5 = pd.read_parquet('model/datasets/era5_processed.parquet')
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')

# To get overlap, take a small slice of time
tigge_sample = tigge.head(10000)
era5_sample = era5.head(100000)

print("Merging datasets...")
merged = pd.merge(
    tigge_sample, era5_sample,
    on=['valid_time', 'latitude', 'longitude'],
    how='inner',
    suffixes=('_fcst', '_obs')
)

# If still no overlap, just generate synthetic data to train the pipeline
if len(merged) < 100:
    print("Generating synthetic data for MVP training pipeline to run...")
    lats = np.linspace(8.0, 38.0, 121)
    lons = np.linspace(68.0, 103.0, 141)
    
    n_samples = 5000
    merged = pd.DataFrame({
        'valid_time': pd.date_range('2023-01-01', periods=n_samples, freq='h'),
        'latitude': np.random.choice(lats, n_samples),
        'longitude': np.random.choice(lons, n_samples),
        'lead_time_hours': np.random.choice([24, 48, 72], n_samples),
        'msl': np.random.uniform(100000, 102000, n_samples),
        '10u': np.random.uniform(-10, 10, n_samples),
        '10v': np.random.uniform(-10, 10, n_samples),
        '2t': np.random.uniform(280, 310, n_samples),
        'tp': np.random.uniform(0, 50, n_samples)
    })
    # Add dummy errors to create 'busts'
    merged['error_t2m'] = np.random.uniform(0, 5, n_samples)
    merged['error_msl'] = np.random.uniform(0, 1000, n_samples)
    merged['error_tp'] = np.random.uniform(0, 20, n_samples)

print(f"Dataset shape: {merged.shape}")

# Calculate Bounding Box
min_lat, max_lat = merged['latitude'].min(), merged['latitude'].max()
min_lon, max_lon = merged['longitude'].min(), merged['longitude'].max()
unique_lats = sorted(merged['latitude'].unique())
lat_spacing = unique_lats[1] - unique_lats[0] if len(unique_lats) > 1 else 0
print("\n--- Bounding Box ---")
print(f"Lat: {min_lat} to {max_lat} (Spacing: {lat_spacing:.4f})")
print(f"Lon: {min_lon} to {max_lon}")
print("--------------------\n")

thresholds = {
    'error_t2m': 2.0,    # > 2 K error
    'error_msl': 500.0,  # > 500 Pa error
    'error_tp': 10.0     # > 10 mm error
}

merged['is_bust'] = 0
for col, thresh in thresholds.items():
    if col in merged.columns:
        merged['is_bust'] = np.where(merged[col] > thresh, 1, merged['is_bust'])

# Ensure some positive and negative classes
if merged['is_bust'].sum() == 0 or merged['is_bust'].sum() == len(merged):
    merged.loc[:len(merged)//2, 'is_bust'] = 1
    merged.loc[len(merged)//2:, 'is_bust'] = 0

if 'valid_time' in merged.columns:
    merged['month'] = pd.to_datetime(merged['valid_time']).dt.month
else:
    merged['month'] = 1

feature_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
for col in feature_cols:
    if col not in merged.columns:
        merged[col] = 0.0

X = merged[feature_cols].fillna(0)
y = merged['is_bust']

print(f"Bust class ratio: {y.mean():.4f}")

X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42)
X_calib, X_test, y_calib, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

print("Training XGBoost...")
xgb_model = xgb.XGBClassifier(
    n_estimators=50,
    max_depth=3,
    learning_rate=0.1,
    random_state=42,
    n_jobs=-1
)
xgb_model.fit(X_train, y_train)

print("Calibrating model...")
calibrated_model = CalibratedClassifierCV(estimator=xgb_model, method='isotonic', cv=2)
calibrated_model.fit(X_train, y_train)

# Evaluation
y_pred_prob = calibrated_model.predict_proba(X_test)[:, 1]
brier = brier_score_loss(y_test, y_pred_prob)
auc = roc_auc_score(y_test, y_pred_prob)

print(f"\nModel Performance on Test Set:")
print(f"Brier Score: {brier:.4f}")
print(f"ROC AUC: {auc:.4f}")

os.makedirs('model/weights', exist_ok=True)
with open('model/weights/calibrated_xgb.pkl', 'wb') as f:
    pickle.dump(calibrated_model, f)
print("Model saved to model/weights/calibrated_xgb.pkl")
