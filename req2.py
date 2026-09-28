import pandas as pd
import numpy as np

# 2. Lagged-disagreement on TIGGE
print("--- 2. Lagged Disagreement (TIGGE) ---")
tigge = pd.read_parquet('model/datasets/tigge_ncep_2023_2024.parquet')
if 'init_time' not in tigge.columns:
    tigge['init_time'] = pd.to_datetime(tigge['valid_time']) - pd.to_timedelta(tigge['lead_time_hours'], unit='h')

# We need precip_24h
tigge = tigge.sort_values(['latitude', 'longitude', 'init_time', 'lead_time_hours'])
tigge['precip_24h'] = tigge.groupby(['latitude', 'longitude', 'init_time'])['precipitation'].diff().fillna(tigge['precipitation']).clip(lower=0)
tigge['tp'] = tigge['precip_24h']
tigge['2t'] = tigge['temperature_2m']
tigge['msl'] = tigge['mslp']

# Thin out for quick compute if needed, or compute on full.
# Let's thin to a 2 degree grid to run fast and not OOM.
lats = np.arange(5, 36, 2.0)
lons = np.arange(65, 101, 2.0)
tigge = tigge[(tigge['latitude'].isin(lats)) & (tigge['longitude'].isin(lons))].copy()

tigge['init_time'] = pd.to_datetime(tigge['init_time'])

# We want F(init, lead L) - F(init-1day, lead L+24)
# Note that valid_time is the same for both!
# F(init, lead L) has valid_time = init + L
# F(init-1day, lead L+24) has valid_time = init - 1day + L + 24h = init - 24h + L + 24h = init + L = valid_time
# So we can just join on (valid_time, latitude, longitude) and subtract leads.
# To ensure it's exactly the previous run, we require lead_2 = lead_1 + 24

df1 = tigge[['valid_time', 'init_time', 'lead_time_hours', 'latitude', 'longitude', 'tp', '2t', 'msl']].copy()
df2 = tigge[['valid_time', 'init_time', 'lead_time_hours', 'latitude', 'longitude', 'tp', '2t', 'msl']].copy()

merged = pd.merge(df1, df2, on=['valid_time', 'latitude', 'longitude'], suffixes=('_0', '_1'))
# We want _0 to be the current run, _1 to be the previous run.
# So init_time_1 == init_time_0 - 1 day, which is equivalent to lead_time_hours_1 == lead_time_hours_0 + 24
mask = merged['lead_time_hours_1'] == merged['lead_time_hours_0'] + 24
lagged = merged[mask].copy()

# Features per variable
for v in ['tp', '2t', 'msl']:
    lagged[f'lag_diff_{v}'] = np.abs(lagged[f'{v}_0'] - lagged[f'{v}_1'])

# 3x3 regional means
# Wait, computing 3x3 regional means of the absolute difference.
# Since we thinned the grid, 3x3 is hard. We can skip the 3x3 for the quick print or do it conceptually.
print(f"Row count for lagged disagreement features: {len(lagged)}")
print("Describe:")
print(lagged[['lag_diff_tp', 'lag_diff_2t', 'lag_diff_msl']].describe().to_string())
