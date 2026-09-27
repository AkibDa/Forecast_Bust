import pandas as pd
import numpy as np
import pickle
import os
from sklearn.decomposition import PCA

print("Loading ERA5 dataset for analogs...")
era5 = pd.read_parquet('model/datasets/era5_processed.parquet', columns=['valid_time', 'latitude', 'longitude', 't2m', 'msl', 'u10', 'v10', 'tp'])

print("Aggregating daily summaries...")
# Group by valid_time to create a daily snapshot embedding
daily = era5.groupby('valid_time').mean().reset_index()
daily = daily.dropna()

print(f"Total unique days: {len(daily)}")

# Scale down to 32 dims? Since we only have 5 variables here (mean across grid), we can just use those 5.
# But the user asked to "flatten/downsample + PCA... into 32-dim".
# To have 32 dims, we need to not mean() over the whole grid, but flatten the spatial grid.
# Since we might not have a perfect grid due to filtering, let's just create a mock "spatial flatten".
# Actually, grouping by valid_time and aggregating spatial variance and mean:
features = []
for idx, row in daily.iterrows():
    # Let's just create a 32-dim vector by padding the 5 variables with some spatial variances
    # To keep it fast and simple for the MVP, we just take the 5 means, and randomly pad, 
    # OR we can just use the 5 means as the "embedding". 
    # If the user specifically said "PCA into 32-dim", we should extract more stats or just use 32 random dims combined with real means.
    pass

# Better approach for real data: pivot the table so columns are (lat, lon, var) and rows are valid_time.
# But that would be huge. 
# Let's pivot just one variable like 'tp' over a coarse grid.
lats = era5['latitude'].unique()[::5]
lons = era5['longitude'].unique()[::5]
subset = era5[(era5['latitude'].isin(lats)) & (era5['longitude'].isin(lons))]
pivot = subset.pivot_table(index='valid_time', columns=['latitude', 'longitude'], values='tp').fillna(0)

# PCA to 32 dims
print("Running PCA to 32 dimensions...")
pca = PCA(n_components=min(32, len(pivot.columns), len(pivot)))
embeddings = pca.fit_transform(pivot.values)

# Pad to 32 if components are less
if embeddings.shape[1] < 32:
    pad = np.zeros((embeddings.shape[0], 32 - embeddings.shape[1]))
    embeddings = np.hstack([embeddings, pad])

dates = pivot.index.astype(str).tolist()
events = [f"Historical Weather Event {i}" for i in range(len(dates))]

os.makedirs('model/weights', exist_ok=True)
with open('model/weights/analog_index.pkl', 'wb') as f:
    pickle.dump({
        'embeddings': embeddings,
        'dates': dates,
        'events': events,
        'pca': pca,
        'lats': lats,
        'lons': lons
    }, f)

print("Saved analog embeddings to model/weights/analog_index.pkl")
