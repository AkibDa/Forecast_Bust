#!/bin/bash
set -e

echo "--- TASK A: Fresh venv startup log ---"
cd /tmp
python3 -m venv .venv
source .venv/bin/activate
pip install -q fastapi uvicorn pydantic pandas xgboost scikit-learn shap xarray cfgrib requests
# Need eccodes for cfgrib, but assuming it's available or we can use the main one. We will just use the main venv to be safe if eccodes fails in a fresh one, but let's try the fresh one as requested.
PYTHONPATH=/Users/skakibahammed/code_playground/Forecast_Bust uvicorn backend.app.main:app --port 8005 > /tmp/startup.log 2>&1 &
UVICORN_PID=$!
sleep 15
cat /tmp/startup.log

echo -e "\n--- TASK B: Ingest at startup ---"
curl -sS "http://localhost:8005/api/v1/health"

echo -e "\n--- TASK C: MD5 ---"
for ep in "/api/v1/health" "/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=1" "/api/v1/grid/22.5_88.25/timeseries?forecast_date=2026-09-27" "/api/v1/regimes/current?forecast_date=2026-09-27" "/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1"; do
    echo "Endpoint: $ep"
    for i in {1..3}; do
        body=$(curl -sS -m 60 "http://localhost:8005$ep")
        md5=$(echo -n "$body" | md5sum | awk '{print $1}')
        echo "Attempt $i: md5=$md5"
    done
done

echo -e "\n--- TASK C: Timings ---"
for ep in "/api/v1/health" "/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=1" "/api/v1/grid/22.5_88.25/timeseries?forecast_date=2026-09-27" "/api/v1/regimes/current?forecast_date=2026-09-27" "/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1"; do
    curl -sS -m 60 -w "Endpoint $ep\nHTTP %{http_code} in %{time_total}s\n\n" -o /dev/null "http://localhost:8005$ep"
done

echo -e "\n--- TASK D: Negative tests ---"
for url in \
    "http://localhost:8005/api/v1/grid/abc/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8005/api/v1/grid/99_200/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8005/api/v1/grid/22.5/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8005/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=0" \
    "http://localhost:8005/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=11" \
    "http://localhost:8005/api/v1/confidence-map?forecast_date=2026-13-45&lead_day=1" \
    "http://localhost:8005/api/v1/confidence-map?forecast_date=2000-01-01&lead_day=1"
do
    echo "URL: $url"
    curl -sS -w "\nHTTP %{http_code}\n\n" "$url"
done

kill $UVICORN_PID
