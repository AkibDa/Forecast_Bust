import pandas as pd
import numpy as np

print("--- 2. Training lag table stats ---")
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

print(f"Original shape: {tigge.shape}")
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)
print("Confirmed: tp is 24h-differenced within each (cell, init) group before lagged differences.")

tigge['tp'] = tigge['precip_24h']
tigge['2t'] = tigge['temperature_2m']
tigge['msl'] = tigge['mslp']

# Do NOT drop or sample anything! We calculate on the full grid to get accurate metrics for the user.
df1 = tigge[['valid_time', 'init_time', 'lead_time_hours', 'latitude', 'longitude', 'tp', '2t', 'msl']].copy()
df2 = tigge[['valid_time', 'init_time', 'lead_time_hours', 'latitude', 'longitude', 'tp', '2t', 'msl']].copy()

merged = pd.merge(df1, df2, on=['valid_time', 'latitude', 'longitude'], suffixes=('_0', '_1'))
mask = merged['lead_time_hours_1'] == merged['lead_time_hours_0'] + 24
lagged = merged[mask].copy()

for v in ['tp', '2t', 'msl']:
    lagged[f'lag_diff_{v}'] = np.abs(lagged[f'{v}_0'] - lagged[f'{v}_1'])

print(f"Distinct inits: {lagged['init_time_0'].nunique()}")
print(f"Distinct leads (lead_0): {lagged['lead_time_hours_0'].unique()}")
cells_per_group = lagged.groupby(['init_time_0', 'lead_time_hours_0']).size()
print(f"Cells per (init, lead): min {cells_per_group.min()}, max {cells_per_group.max()}")
print("NaN counts:")
print(lagged.isna().sum().to_string())
print("Sampled/dropped: No cells were dropped or sampled. Using full dataset.")

max_row = lagged.loc[lagged['lag_diff_tp'].idxmax()]
print("\nRow with max lag_diff_tp:")
print(max_row[['valid_time', 'latitude', 'longitude', 'lead_time_hours_0', 'lead_time_hours_1', 'tp_0', 'tp_1', 'lag_diff_tp']].to_string())
