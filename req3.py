import sys
import pandas as pd
import numpy as np

sys.path.append('backend')
from app.ingestion import _download_gfs_grib, process_grib_to_schema

# We need today's Day 1 (2026-09-27 lead 24) and yesterday's Day 2 (2026-09-26 lead 48)
print("--- 3. Live Path Lagged Disagreement ---")

path_today = _download_gfs_grib('20260927', '00', '024')
df_today = process_grib_to_schema(path_today)
df_today = df_today[df_today['lead_time_hours'] == 24].copy()

path_yesterday = _download_gfs_grib('20260926', '00', '048')
df_yesterday = process_grib_to_schema(path_yesterday)
df_yesterday = df_yesterday[df_yesterday['lead_time_hours'] == 48].copy()

merged = pd.merge(df_today, df_yesterday, on=['latitude', 'longitude'], suffixes=('_today', '_yest'))

for v in ['tp', '2t', 'msl']:
    merged[f'lag_diff_{v}'] = np.abs(merged[f'{v}_today'] - merged[f'{v}_yest'])

print("Values for 3 cells:")
print(merged[['latitude', 'longitude', 'lag_diff_tp', 'lag_diff_2t', 'lag_diff_msl']].head(3).to_string())
