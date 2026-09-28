#!/bin/bash
set -e

cd /Users/skakibahammed/code_playground/Forecast_Bust/backend
source ../.venv/bin/activate

uvicorn app.main:app --port 8011 > startup_local.log 2>&1 &
UVICORN_PID=$!
sleep 15
echo "--- TASK A: startup log (from local venv just in case) ---"
cat startup_local.log

echo -e "\n--- TASK B: /health ---"
curl -sS "http://localhost:8011/api/v1/health"

echo -e "\n--- TASK C: MD5 ---"
for ep in "/api/v1/health" "/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=1" "/api/v1/grid/22.5_88.25/timeseries?forecast_date=2026-09-27" "/api/v1/regimes/current?forecast_date=2026-09-27" "/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1"; do
    echo "Endpoint: $ep"
    for i in {1..3}; do
        body=$(curl -sS -m 60 "http://localhost:8011$ep")
        md5=$(echo -n "$body" | md5sum | awk '{print $1}')
        echo "Attempt $i: md5=$md5"
    done
done

echo -e "\n--- TASK C: Timings ---"
for ep in "/api/v1/health" "/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=1" "/api/v1/grid/22.5_88.25/timeseries?forecast_date=2026-09-27" "/api/v1/regimes/current?forecast_date=2026-09-27" "/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1"; do
    curl -sS -m 60 -w "Endpoint $ep\nHTTP %{http_code} in %{time_total}s\n\n" -o /dev/null "http://localhost:8011$ep"
done

echo -e "\n--- TASK D: Negative tests ---"
for url in \
    "http://localhost:8011/api/v1/grid/abc/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8011/api/v1/grid/99_200/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8011/api/v1/grid/22.5/timeseries?forecast_date=2026-09-27" \
    "http://localhost:8011/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=0" \
    "http://localhost:8011/api/v1/confidence-map?forecast_date=2026-09-27&lead_day=11" \
    "http://localhost:8011/api/v1/confidence-map?forecast_date=2026-13-45&lead_day=1" \
    "http://localhost:8011/api/v1/confidence-map?forecast_date=2000-01-01&lead_day=1"
do
    echo "URL: $url"
    echo -n "Status: "
    curl -sS -o /dev/null -w "%{http_code}\n" "$url"
    echo -n "Body: "
    curl -sS "$url"
    echo -e "\n"
done

kill $UVICORN_PID
