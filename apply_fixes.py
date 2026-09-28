import os

# 1. Update feature_provider.py
with open("backend/app/feature_provider.py", "r") as f:
    feat = f.read()

# Replace get_coverage
old_get_coverage = """def get_coverage(mode: str):
    if mode == "historical":
        return {"start": "2023-01-01", "end": "2024-12-31"}
    return {"start": "2026-09-27", "end": "2026-09-27"}"""
new_get_coverage = """def get_coverage(mode: str = None):
    _load_historical_data()
    historical_dates = sorted(_tigge_df['init_time'].dt.strftime('%Y-%m-%d').unique().tolist())
    from .ingestion import status
    live_cycle = []
    if status.last_status == "success" and status.mode in ["live", "cache"] and status.last_success_time:
        if isinstance(status.last_success_time, str):
            live_cycle = [status.last_success_time.split("T")[0]]
    if mode == "historical":
        return historical_dates
    elif mode == "live":
        return live_cycle
    return {"historical": historical_dates, "live": live_cycle}"""
feat = feat.replace(old_get_coverage, new_get_coverage)

old_404 = """detail=f"Historical data not found for init_time={forecast_date} and lead_day={lead_day}. Available dates range from {_tigge_df['init_time'].min().date()} to {_tigge_df['init_time'].max().date()}""""
new_404 = """detail=f"Historical data not found for init_time={forecast_date} and lead_day={lead_day}. Available dates: {get_coverage('historical')}""""
feat = feat.replace(old_404, new_404)

with open("backend/app/feature_provider.py", "w") as f:
    f.write(feat)

# 2. Update health.py
with open("backend/app/health.py", "r") as f:
    health = f.read()

# Replace coverage call
health = health.replace('from .feature_provider import get_coverage', 'from .feature_provider import get_coverage')
health = health.replace('data_coverage_range=get_coverage(mode)', 'data_coverage_range=get_coverage()')
with open("backend/app/health.py", "w") as f:
    f.write(health)

# 3. Update main.py to add /api/v1/coverage
with open("backend/app/main.py", "r") as f:
    main = f.read()

if "/api/v1/coverage" not in main:
    coverage_endpoint = """
@app.get("/api/v1/coverage")
def coverage():
    from .feature_provider import get_coverage
    return get_coverage()
"""
    main = main + coverage_endpoint
with open("backend/app/main.py", "w") as f:
    f.write(main)

# 4. Update analog_retrieval.py
with open("backend/app/analog_retrieval.py", "r") as f:
    analog = f.read()

analog_replacement = """
    for _, row in top_n.iterrows():
        case_dt = row['valid_time']
        if isinstance(case_dt, str):
            case_date_str = case_dt.split("T")[0]
        else:
            case_date_str = case_dt.strftime("%Y-%m-%d")

        # Domain max/mean ERA5 precip and location
        # Since we just have the row, the "domain" max/mean isn't in this row, but the user says "domain max/mean ERA5 precip and its location"
        # We need to find the max precip in era5 for that day. 
        # Actually, let's just use the `error_tp` or `is_bust` from the row as the forecast-error outcome.
        
        # Real facts per analog
        out = {
            "case_date": case_date_str,
            "similarity_score": round(row['similarity'], 3),
            "domain_max_precip": None, # Will fill this
            "domain_mean_precip": None,
            "max_precip_location": None,
            "forecast_error_outcome": f"Bust={row['is_bust']}" if 'is_bust' in row else None
        }
        analogs.append(out)
"""
# wait, actually, to get domain max/mean ERA5 precip and its location, we need era5. Let's do it in the file.
