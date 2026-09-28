# Helper script to perform the code updates

import os
import re

# 1 & 2. main.py: Model eager load, Date format validation
main_path = "backend/app/main.py"
with open(main_path, "r") as f:
    main_code = f.read()

main_code = main_code.replace(
    'def startup_event():\n    try:\n        run_ingestion_pipeline()',
    'def startup_event():\n    from .model_interface import _load_model\n    _load_model()\n    try:\n        run_ingestion_pipeline()'
)

# Date validation dependency
if "from datetime import datetime" not in main_code:
    main_code = "from datetime import datetime\n" + main_code

# Date validator function
date_validator = """
def validate_date(date_str: str):
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
"""
main_code = main_code.replace('@app.get("/api/v1/health"', date_validator + '\n@app.get("/api/v1/health"')

# Add date validation to endpoints
main_code = main_code.replace('def confidence_map(forecast_date: str, lead_day: int):', 'def confidence_map(forecast_date: str, lead_day: int):\n    validate_date(forecast_date)')
main_code = main_code.replace('def timeseries(grid_id: str, forecast_date: str):', 'def timeseries(grid_id: str, forecast_date: str):\n    validate_date(forecast_date)')
main_code = main_code.replace('def explanation(grid_id: str, forecast_date: str, lead_day: int):', 'def explanation(grid_id: str, forecast_date: str, lead_day: int):\n    validate_date(forecast_date)')

with open(main_path, "w") as f:
    f.write(main_code)

# 2. Grid validation in feature_provider.py
feature_path = "backend/app/feature_provider.py"
with open(feature_path, "r") as f:
    feat_code = f.read()

# Add coverage function
coverage_fn = """
def get_coverage(mode: str):
    if mode == "historical":
        return {"start": "2023-01-01", "end": "2024-12-31"}
    return {"start": "2026-09-27", "end": "2026-09-27"}
"""
feat_code = feat_code.replace('import os', 'import os\nfrom .config import DOMAIN\n' + coverage_fn)

grid_val = """
    if not (DOMAIN["lat_min"] <= lat <= DOMAIN["lat_max"] and DOMAIN["lon_min"] <= lon <= DOMAIN["lon_max"]):
        raise ValueError(f"grid_id {grid_id} outside domain bounding box")
"""
feat_code = feat_code.replace('lon = float(parts[1])', 'lon = float(parts[1])\n' + grid_val)

# Fix live lead_day validation to throw ValueError formatting supported_lead_days
feat_code = feat_code.replace(
    'raise ValueError("supported_lead_days=[1] for live/cache mode in MVP")',
    'raise ValueError("supported_lead_days=[1]")'
)

# Fix 404 message to use get_coverage
feat_code = feat_code.replace(
    'raise ValueError(f"Historical data not found for init_time={init_time_str} and lead_day={lead_day}. Available dates range from 2023-01-01 to 2024-12-31")',
    'cov = get_coverage("historical")\n        raise ValueError(f"Historical data not found for init_time={init_time_str} and lead_day={lead_day}. Available dates range from {cov[\'start\']} to {cov[\'end\']}")'
)
with open(feature_path, "w") as f:
    f.write(feat_code)


# 1 & 4. health.py: True model loaded state & coverage
health_path = "backend/app/health.py"
with open(health_path, "r") as f:
    health_code = f.read()

health_code = health_code.replace(
    'from .config import DOMAIN',
    'from .config import DOMAIN\nfrom .feature_provider import get_coverage'
)
health_code = health_code.replace(
    'data_coverage_range={"start": "2023-01-01", "end": "2026-09-19"},',
    'data_coverage_range=get_coverage(ingestion_info["mode"]),'
)
# Add supported_lead_days
health_code = health_code.replace(
    'grid_domain: Dict[str, Any]',
    'grid_domain: Dict[str, Any]\n    supported_lead_days: list = [1]'
)
health_code = health_code.replace(
    'grid_domain=DOMAIN',
    'grid_domain=DOMAIN,\n        supported_lead_days=[1] if ingestion_info["mode"] in ["live", "cache"] else [1,2,3,4,5,6,7,8,9,10]'
)
with open(health_path, "w") as f:
    f.write(health_code)


# 3. ingestion.py: explicitly filter stepRange=0-24
ingest_path = "backend/app/ingestion.py"
with open(ingest_path, "r") as f:
    ingest_code = f.read()

ingest_code = ingest_code.replace(
    "ds_list = cfgrib.open_datasets(grib_path)",
    "ds_list = cfgrib.open_datasets(grib_path, backend_kwargs={'filter_by_keys': {'stepRange': '0-24', 'shortName': 'tp'}})\n    ds_list_others = cfgrib.open_datasets(grib_path, backend_kwargs={'filter_by_keys': {'stepType': 'instant'}})\n    ds_list = ds_list + ds_list_others"
)
with open(ingest_path, "w") as f:
    f.write(ingest_code)

# main.py valueerror mapper to 422 if it's validation
main_code = open(main_path).read()
main_code = main_code.replace(
    'def general_exception_handler(request: Request, exc: Exception):\n    return JSONResponse(\n        status_code=500,',
    'def general_exception_handler(request: Request, exc: Exception):\n    status_code = 422 if isinstance(exc, ValueError) else 500\n    return JSONResponse(\n        status_code=status_code,'
)
with open(main_path, "w") as f:
    f.write(main_code)
