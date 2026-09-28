import sys
import pandas as pd
import numpy as np
import os
sys.path.append('backend')
from app.ingestion import process_grib_to_schema

# --- 4. Live Feature Statistics ---
cache_path = "model/datasets/gfs_cached_demo.grb2"
live_df = process_grib_to_schema(cache_path)
live_df = live_df[live_df['lead_time_hours'] == 24].copy()
live_df['month'] = 9

expected_cols = ['lead_time_hours', 'latitude', 'longitude', 'month', 'msl', '10u', '10v', '2t', 'tp']
print("\nLive feature statistics (2026-09-27 lead 1):")
print(live_df[expected_cols].describe().to_string())

from app.model_interface import predict_batch, _load_model
_load_model()
live_df_mod = live_df.copy()
live_df_mod['month'] = 6  # simulate train month
preds = predict_batch(live_df_mod)
mean_prob = preds['bust_probability'].mean()
print(f"\nMean predicted probability for the live day when month is set to 6: {mean_prob:.4f}")
