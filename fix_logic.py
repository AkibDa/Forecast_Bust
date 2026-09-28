import os
import re

# Fix health.py to check dynamically
health_path = "backend/app/health.py"
with open(health_path, "r") as f:
    h_code = f.read()

h_code = h_code.replace(
    'try:\n        if _model is None:\n            _load_model()\n        model_loaded = _model is not None\n    except Exception:\n        model_loaded = False',
    'try:\n        import backend.app.model_interface as mi\n        model_loaded = mi._model is not None\n    except Exception:\n        model_loaded = False'
)
with open(health_path, "w") as f:
    f.write(h_code)

# Fix feature_provider.py for out-of-domain and lead_day to not be swallowed by 503
feat_path = "backend/app/feature_provider.py"
with open(feat_path, "r") as f:
    f_code = f.read()

f_code = f_code.replace(
    'if not (DOMAIN["lat_min"] <= lat <= DOMAIN["lat_max"] and DOMAIN["lon_min"] <= lon <= DOMAIN["lon_max"]):\n        raise ValueError(f"grid_id {grid_id} outside domain bounding box")',
    ''
)
# Place it at the beginning of get_forecast_features
f_code = f_code.replace(
    'def get_forecast_features(grid_id: str, init_time_str: str, lead_time_hours: int, mode: str = "historical") -> dict:\n    parts = grid_id.split("_")',
    'def get_forecast_features(grid_id: str, init_time_str: str, lead_time_hours: int, mode: str = "historical") -> dict:\n    parts = grid_id.split("_")\n    lat = float(parts[0])\n    lon = float(parts[1])\n    if not (DOMAIN["lat_min"] <= lat <= DOMAIN["lat_max"] and DOMAIN["lon_min"] <= lon <= DOMAIN["lon_max"]):\n        raise ValueError(f"grid_id {grid_id} outside domain bounding box. Expected lat in [{DOMAIN[\'lat_min\']}, {DOMAIN[\'lat_max\']}], lon in [{DOMAIN[\'lon_min\']}, {DOMAIN[\'lon_max\']}]")'
)

# And for confidence map which iterates, it doesn't use get_forecast_features. Wait! It does use predict_batch. Let's add grid validation to the endpoints directly.
main_path = "backend/app/main.py"
with open(main_path, "r") as f:
    m_code = f.read()

grid_validator = """
def validate_grid(grid_id: str):
    from .config import DOMAIN
    try:
        parts = grid_id.split("_")
        lat = float(parts[0])
        lon = float(parts[1])
        if not (DOMAIN["lat_min"] <= lat <= DOMAIN["lat_max"] and DOMAIN["lon_min"] <= lon <= DOMAIN["lon_max"]):
            raise ValueError(f"grid_id {grid_id} outside domain")
    except Exception:
        raise ValueError(f"Invalid grid_id {grid_id}")
"""
m_code = m_code.replace('def validate_date(date_str: str):', grid_validator + '\ndef validate_date(date_str: str):')

m_code = m_code.replace(
    'def timeseries(grid_id: str, forecast_date: str):\n    validate_date(forecast_date)',
    'def timeseries(grid_id: str, forecast_date: str):\n    validate_date(forecast_date)\n    validate_grid(grid_id)'
)
m_code = m_code.replace(
    'def explanation(grid_id: str, forecast_date: str, lead_day: int):\n    validate_date(forecast_date)',
    'def explanation(grid_id: str, forecast_date: str, lead_day: int):\n    validate_date(forecast_date)\n    validate_grid(grid_id)'
)
# For lead_day > 1
m_code = m_code.replace(
    'if lead_day < 1 or lead_day > 10:\n        raise HTTPException(status_code=422, detail="lead_day must be between 1 and 10")',
    'if lead_day < 1 or lead_day > 10:\n        raise ValueError("lead_day must be between 1 and 10")\n    from .ingestion import get_ingestion_status\n    st = get_ingestion_status()\n    if st["mode"] in ["live", "cache"] and lead_day > 1:\n        raise ValueError("supported_lead_days=[1] in live mode")'
)

with open(main_path, "w") as f:
    f.write(m_code)

print("Fixed logic.")
