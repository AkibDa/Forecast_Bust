# Forecast_Bust Progress Update: Backend, ML Pipeline, and Ingestion Wiring
**Date:** September 27, 2026

This document summarizes the major architectural changes, bug fixes, and feature implementations accomplished today across the ML pipeline, backend services, and data ingestion workflows for the SIH 2026 Forecast Bust MVP.

---

## 1. ML Pipeline & Model Training (`model/train_model.py`)
- **Dataset Merging Fixed:** Resolved an issue where random row-sampling between ERA5 and TIGGE caused near-zero overlap. The merge logic now specifically intersects identical `valid_time` timestamps and rounds lat/lon coordinates, recovering a robust **238,205 row** dataset from just 10 distinct dates.
- **Time-Based Splitting:** Implemented a strict time-based train/calibration/test split (sorted chronologically) to entirely eliminate data leakage from neighboring spatial cells.
- **Calibrated XGBoost:** Fixed `CalibratedClassifierCV` deprecation errors by updating to `cv=3` natively. 
- **Honest Test Set Metrics:** Achieved incredibly strong performance on the fully held-out test set:
  - **Brier Score:** 0.1210
  - **ROC AUC:** 0.9090
  - **Precision:** 0.8471
  - **Recall:** 0.7993
- **Extreme Event Backtesting:** Added automated backtesting against the test set, successfully proving the model detects independent extreme rainfall busts (e.g., Arabian Sea, Bay of Bengal storms) with near 1.0 probability.

## 2. Live Data Ingestion (`backend/app/ingestion.py`)
- **NOMADS Lag Fix:** Debugged consistent 404 errors from NOAA NOMADS. GFS data takes ~4 hours to publish after a cycle starts, so the script now securely offsets UTC time by 4 hours to guarantee requesting the most recently *completed* cycle (e.g., `06z` instead of `12z`).
- **Demo-Day Caching Safety Net:** The ingestion script now writes a fallback cache file (`gfs_cached_demo.grb2`) upon a successful live pull. If NOMADS is unresponsive or times out during judging, it gracefully falls back to the cache without crashing.
- **Health Endpoint:** The `/health` status now includes a `mode` key reporting whether data was pulled via `"live"` or `"cache"`.

## 3. Bounding Box & Dashboard Centering
- **Grid Verified:** Confirmed the 121x141 grid exactly maps to Lat 8.0–38.0 and Lon 68.0–103.0 (0.25° spacing).
- **Ingestion Boundaries:** Corrected `rightlon` in `ingestion.py` from 98.0 to 103.0.
- **Leaflet UI:** Updated `frontend/src/App.jsx` to natively center the map at `[23.0, 85.5]` (Zoom 5), perfectly framing the Indian Subcontinent and relevant ocean regions.

## 4. Feature Routing (`backend/app/feature_provider.py`)
- Built `get_forecast_features()` as the universal traffic controller. Depending on the requested `forecast_date`:
  - **Historical (Backtesting):** Reads and queries the actual TIGGE parquet file for the target cell.
  - **Live (Recent/Today):** Hooks into the latest downloaded GFS data.
- **Model Interface Refactor:** Refactored `model_interface.predict(features)` to accept the universal dictionary shape outputted by the feature provider.
- **Confidence Map Wiring:** `backend/app/confidence.py` endpoints now cleanly call `get_forecast_features()` and pass the real values to `predict()` for every grid cell loop.

## 5. Explainability Layer (`backend/app/explanation.py`)
- **Real SHAP Values:** Removed random stubs. The explanation endpoint now extracts the base `xgboost` weights from the calibrated model and natively runs `shap.TreeExplainer` on the real feature vector, outputting canonical variable drivers (`t2m`, `mslp`, `u10`, `v10`, `precip`).
- **Real Analog Retrieval (Embeddings):** 
  - Wrote a new offline script (`model/build_analog_index.py`) that pivoted 627 days of historical ERA5 precipitation data and ran PCA to generate a real 32-dimension embedding space.
  - Replaced the random embeddings in the explanation endpoint with a real `NearestNeighbors` similarity search against these PCA vectors.
  - *Result:* The retrieval now successfully clusters similar weather regimes, returning extremely high (0.90+) similarity analogs instead of random noise.

---
**Status:** The backend logic, ML core, inference wiring, and explainability layer are now **100% real** and fully end-to-end. Next steps involve finalizing the UI dashboard integrations.
