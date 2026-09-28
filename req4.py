import os
import sys
import shutil

sys.path.append('backend')
from app.ingestion import download_latest_gfs, status

print("--- 4. Regenerate GRIB Demo Cache ---")
try:
    path = download_latest_gfs(24)
    cache_path = "model/datasets/gfs_cached_demo.grb2"
    backup_path = "model/datasets/backup/gfs_cached_demo.grb2"
    
    # download_latest_gfs saves it to cache path relative to backend/app.
    # It saves to `../model/datasets/gfs_cached_demo.grb2` which is `backend/../model/datasets/...`
    # meaning `model/datasets/...` from the project root.
    
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    if os.path.exists(cache_path):
        shutil.copy(cache_path, backup_path)
        print(f"Backed up to {backup_path}")
    
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    response = client.get("/api/v1/health")
    print("\n/health response:")
    import json
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
