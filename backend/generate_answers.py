import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.calibration import calibration_curve
import sys

print("Loading datasets...")
tigge = pd.read_parquet('../model/datasets/tigge_ncep_2023_2024.parquet')
era5 = pd.read_parquet('../model/datasets/era5_processed.parquet')

# 1. TIGGE
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

print("\n1. TIGGE")
print(f"min/max init_time: {tigge['init_time'].min()} / {tigge['init_time'].max()}")
print(f"min/max valid_time: {tigge['valid_time'].min()} / {tigge['valid_time'].max()}")
print(f"# distinct init_times: {tigge['init_time'].nunique()}")
print(f"sorted distinct lead_time_hours: {np.sort(tigge['lead_time_hours'].unique())}")
print(f"min/max lat: {tigge['latitude'].min()} / {tigge['latitude'].max()}")
print(f"min/max lon: {tigge['longitude'].min()} / {tigge['longitude'].max()}")
print(f"# distinct lats: {tigge['latitude'].nunique()}, # distinct lons: {tigge['longitude'].nunique()}")

# 2. ERA5
print("\n2. ERA5")
print(f"min/max valid_time: {era5['valid_time'].min()} / {era5['valid_time'].max()}")
print(f"# distinct dates: {pd.to_datetime(era5['valid_time']).dt.date.nunique()}")
print(f"hours-of-day present: {pd.to_datetime(era5['valid_time']).dt.hour.unique()}")
print(f"min/max lat: {era5['latitude'].min()} / {era5['latitude'].max()}")
print(f"min/max lon: {era5['longitude'].min()} / {era5['longitude'].max()}")

# 3. Overlap
shared_valid = np.intersect1d(era5['valid_time'].unique(), tigge['valid_time'].unique())
shared_valid_sorted = np.sort(shared_valid)
print("\n3. Overlap")
print(f"# shared valid_times: {len(shared_valid)}")
print(f"list of shared valid_times: {shared_valid_sorted}")

tigge_sub = tigge[tigge['valid_time'].isin(shared_valid)].copy()
tigge_sub['latitude'] = tigge_sub['latitude'].round(2)
tigge_sub['longitude'] = tigge_sub['longitude'].round(2)
era5_sub = era5[era5['valid_time'].isin(shared_valid)].copy()
era5_sub['latitude'] = era5_sub['latitude'].round(2)
era5_sub['longitude'] = era5_sub['longitude'].round(2)

merged = pd.merge(tigge_sub, era5_sub, on=['valid_time', 'latitude', 'longitude'], how='inner', suffixes=('_fcst', '_obs'))
print(f"# distinct (init_time, lead) pairs in merged: {merged[['init_time', 'lead_time_hours']].drop_duplicates().shape[0]}")
n_lat_lon = merged[['latitude', 'longitude']].drop_duplicates().shape[0]
print(f"merged rows / (n_lat * n_lon): {len(merged) / n_lat_lon:.2f}")

# 4. Normalization samples
group_counts = merged.groupby(['latitude', 'longitude', 'lead_time_hours']).size()
print("\n4. train_model.py normalization")
print(f"samples per (lat, lon, lead) group - min: {group_counts.min()}, median: {group_counts.median()}, max: {group_counts.max()}")
print("whether mean/std use the train period only: No (currently uses the entire merged dataset before time-based split)")

# 5. lead_time_hours step for tp .diff()
sample_cell = tigge[(tigge['latitude'] == tigge['latitude'].iloc[0]) & 
                    (tigge['longitude'] == tigge['longitude'].iloc[0]) &
                    (tigge['init_time'] == tigge['init_time'].iloc[0])].sort_values('lead_time_hours')
steps = sample_cell['lead_time_hours'].diff().dropna().unique()
print("\n5. lead_time_hours step actually used by tp .diff()")
print(f"Step(s): {steps} hours")

# 6. Baseline AUC/Brier [lead, lat, lon, month] and reliability
print("\n6. Baseline & Reliability")
merged['month'] = pd.to_datetime(merged['valid_time']).dt.month
merged['raw_err_t2m'] = merged['temperature_2m'] - merged['t2m']
merged['raw_err_msl'] = merged['mslp'] - merged['msl']
merged['raw_err_tp'] = merged['precipitation'] - merged['tp']
group_cols = ['latitude', 'longitude', 'lead_time_hours']
stats = merged.groupby(group_cols)[['raw_err_t2m', 'raw_err_msl', 'raw_err_tp']].agg(['mean', 'std']).reset_index()
stats.columns = group_cols + ['mean_err_t2m', 'std_err_t2m', 'mean_err_msl', 'std_err_msl', 'mean_err_tp',  'std_err_tp']
merged = pd.merge(merged, stats, on=group_cols, how='left')
merged['z_t2m'] = np.abs(merged['raw_err_t2m'] - merged['mean_err_t2m']) / (merged['std_err_t2m'] + 1e-6)
merged['z_msl'] = np.abs(merged['raw_err_msl'] - merged['mean_err_msl']) / (merged['std_err_msl'] + 1e-6)
merged['z_tp']  = np.abs(merged['raw_err_tp'] - merged['mean_err_tp']) / (merged['std_err_tp'] + 1e-6)
merged['max_z'] = merged[['z_t2m', 'z_msl', 'z_tp']].max(axis=1)
q90 = merged.groupby('lead_time_hours')['max_z'].quantile(0.90).reset_index(name='q90_z')
merged = pd.merge(merged, q90, on='lead_time_hours', how='left')
merged['is_bust'] = (merged['max_z'] > merged['q90_z']).astype(int)

merged = merged.sort_values('valid_time')
n_total = len(merged)
train_idx = int(n_total * 0.7)
test_data = merged.iloc[int(n_total * 0.85):]
train_data = merged.iloc[:train_idx]

features = ['lead_time_hours', 'latitude', 'longitude', 'month']
X_train = train_data[features]
y_train = train_data['is_bust']
X_test = test_data[features]
y_test = test_data['is_bust']

model_b = xgb.XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1)
model_b.fit(X_train, y_train)
pred_b = model_b.predict_proba(X_test)[:, 1]
print(f"Baseline (lead, lat, lon, month) - AUC: {roc_auc_score(y_test, pred_b):.4f}, Brier: {brier_score_loss(y_test, pred_b):.4f}")

# Re-run full model to get predictions for reliability table
import pickle
with open('../model/weights/calibrated_xgb.pkl', 'rb') as f:
    full_model = pickle.load(f)
    full_features = ['lead_time_hours', 'latitude', 'longitude', 'month', 'mslp', 'u10_fcst', 'v10_fcst', 'temperature_2m', 'precipitation']
    X_test_full = test_data[full_features].rename(columns={'mslp': 'msl', 'temperature_2m': '2t', 'precipitation': 'tp', 'u10_fcst': '10u', 'v10_fcst': '10v'})
full_pred = full_model.predict_proba(X_test_full)[:, 1]

prob_true, prob_pred = calibration_curve(y_test, full_pred, n_bins=10)
print("\nReliability Table (Full Model on Test Set):")
print("Bin | Mean Predicted Prob | True Fraction of Busts")
for i in range(len(prob_true)):
    print(f"{i+1:2d}  | {prob_pred[i]:.4f}            | {prob_true[i]:.4f}")
