# Forecast Bust Detection — API Contract (v1)

**Status:** FROZEN for Day 2 start, with two fields explicitly marked provisional (see below).
**Owner of backend implementation:** Akib (explainability/confidence endpoints), Jeet (ingestion/dashboard-facing endpoints)
**Consumer:** Jeet's dashboard, Susovan's model outputs feed into this via Akib's fusion layer

---

## Resolved (confirmed against actual processed data)

1. **Region encoding — grid-based, not subdivision-based.** Processed ERA5/TIGGE data is a 121×141 lat/lon grid. `region_id` is replaced by `grid_id = "<lat>_<lon>"`, with raw `latitude`/`longitude` also included in every response for direct map plotting. **Open sub-item:** Susovan to share the actual lat/lon bounding box of the 121×141 grid so Jeet can set the dashboard's default map extent.
2. **Feature names — use actual processed variables, not engineered ones.** Available now: TIGGE forecast variables `temperature_2m, u10, v10, mslp, precipitation`; ERA5 reference variables `t2m, d2m, msl, sp, sst, u10, v10, tp` (+ wave variables). No ensemble spread, MJO phase, or CAPE gradient exist yet — these were placeholders and are removed from this contract. `top_drivers` in the explanation endpoint now references raw variable names only.
3. **Regime tags — not finalized, field is provisional.** No clustering/regime output exists yet. `regime_tag` is kept in the schema as a **nullable** field (`null` until Susovan's clustering step is built) so downstream code doesn't have to change shape later — just start returning real values once available.

**DECIDED — ensemble spread is out of scope for the MVP.** Confirmed: the processed NCEP TIGGE dataset contains only the control forecast (`cf`), not perturbed members (`pf`), so within-model ensemble spread cannot be computed from current data. Downloading/reprocessing PF members mid-sprint would displace core model training time, so it is deferred.

**Core confidence signal for the MVP instead:** learn historical forecast error directly from the data already available — control forecast fields (`msl, 10u, 10v, 2t, tp`) vs ERA5 truth, conditioned on `lead_time_hours`, `latitude`, `longitude`, and season/time-of-year. This is a fully supervised, learnable problem with the existing 31.6M-row dataset and needs no member dimension. Ensemble spread (and separately, multi-model GFS-vs-ECMWF disagreement) are documented as roadmap extensions, not MVP dependencies.

---

## Conventions

- Dates: ISO 8601, `YYYY-MM-DD` (e.g. `"2026-09-26"`)
- `lead_day`: integer, 1–10
- `grid_id`: string, `"<lat>_<lon>"` (e.g. `"22.5_88.25"`) — replaces the earlier `region_id` concept
- `latitude`, `longitude`: floats, included alongside `grid_id` in every response for direct plotting
- `confidence_score`: float, 0.0–1.0, calibrated (higher = more confident forecast)
- `bust_probability`: float, 0.0–1.0 (higher = more likely to bust)
- `regime_tag`: string or `null` — **provisional**, will be `null` until regime classification is built
- All responses: `application/json` except confidence-map, which is `GeoJSON`
- Errors: `{ "error": { "code": "string", "message": "string" } }`, standard HTTP status codes

---

## Endpoints

### 1. `GET /api/v1/confidence-map`

Region-wise confidence + bust probability for a given forecast issue date and lead day, as GeoJSON for map rendering.

**Query params:**
- `forecast_date` (required) — date the forecast was issued
- `lead_day` (required) — 1 to 10

**Response:** `GeoJSON FeatureCollection` (one Point feature per grid cell)
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [88.25, 22.5] },
      "properties": {
        "grid_id": "22.5_88.25",
        "latitude": 22.5,
        "longitude": 88.25,
        "confidence_score": 0.42,
        "bust_probability": 0.58,
        "regime_tag": null
      }
    }
  ]
}
```
*Note: dashboard should render grid points (or an interpolated heatmap over them), not administrative-boundary polygons, since the underlying data has no subdivision geometry.*

---

### 2. `GET /api/v1/grid/{grid_id}/timeseries`

Confidence/bust probability across Day 1–10 for one grid cell — powers the dashboard's lead-time slider/trend view. `grid_id` is `"<lat>_<lon>"`, e.g. `/api/v1/grid/22.5_88.25/timeseries`.

**Query params:**
- `forecast_date` (required)

**Response:**
```json
{
  "grid_id": "22.5_88.25",
  "latitude": 22.5,
  "longitude": 88.25,
  "forecast_date": "2026-09-26",
  "lead_times": [
    { "lead_day": 1, "confidence_score": 0.91, "bust_probability": 0.09 },
    { "lead_day": 2, "confidence_score": 0.85, "bust_probability": 0.15 },
    { "lead_day": 3, "confidence_score": 0.58, "bust_probability": 0.42 }
  ]
}
```

---

### 3. `GET /api/v1/grid/{grid_id}/explanation`

Explainability payload: feature-level drivers (SHAP) + historical analog cases. Powers the dashboard's drill-down panel. `top_drivers` currently reference **raw processed variables only** (no engineered features exist yet — see Resolved #2 above).

**Query params:**
- `forecast_date` (required)
- `lead_day` (required)

**Response:**
```json
{
  "grid_id": "22.5_88.25",
  "lead_day": 3,
  "regime_tag": null,
  "top_drivers": [
    { "feature": "mslp", "contribution": 0.31, "direction": "lowers_confidence" },
    { "feature": "precipitation", "contribution": 0.18, "direction": "lowers_confidence" },
    { "feature": "u10", "contribution": -0.12, "direction": "raises_confidence" }
  ],
  "analogs": [
    {
      "case_date": "2021-07-18",
      "event_name": "Uttarakhand rainfall bust",
      "similarity_score": 0.87,
      "historical_error_summary": "Day-3 rainfall forecast under-predicted by 40mm+; observed bust"
    }
  ]
}
```
*`feature` values must exactly match whatever variable names Susovan's model actually uses internally (`t2m` vs `temperature_2m`, `msl` vs `mslp`, etc. — TIGGE and ERA5 use slightly different names for the same quantities). Akib and Susovan to agree on ONE canonical name per variable before wiring SHAP — see naming note below.*

---

### 4. `GET /api/v1/regimes/current`

**NOT ACTIVE until Susovan's clustering step exists.** Endpoint is defined now so the dashboard can scaffold against it, but should return `501 Not Implemented` (or a static "not yet available" response) until real regime output exists. Do not build dashboard UI that depends on this returning real data before Day 3.

**Query params:**
- `forecast_date` (required)

**Response (once implemented):**
```json
{
  "forecast_date": "2026-09-26",
  "regime_tag": "monsoon_depression",
  "regime_description": "Active monsoon depression over Bay of Bengal, weak steering flow",
  "classification_confidence": 0.79
}
```

---

## Canonical variable naming (resolve before wiring SHAP)

TIGGE and ERA5 use different names for overlapping quantities. Pick ONE canonical name per variable for use across the API and SHAP output — proposed below, Susovan to confirm or override:

| Canonical name (use in API) | TIGGE source field | ERA5 source field |
|---|---|---|
| `t2m` | `temperature_2m` | `t2m` |
| `mslp` | `mslp` | `msl` |
| `u10` | `u10` | `u10` |
| `v10` | `v10` | `v10` |
| `precip` | `precipitation` | `tp` |
| `d2m` | — | `d2m` |
| `sp` | — | `sp` |
| `sst` | — | `sst` |

*(Wave variables from ERA5 not yet mapped — add once Susovan confirms which ones are used in the model.)*

---

### 5. `GET /api/v1/health`

Basic liveness check for the demo/integration testing.

**Response:** `{ "status": "ok", "model_version": "v1", "last_ingestion": "2026-09-26T06:00:00Z" }`

---

## Ownership at implementation time

| Endpoint | Built by | Depends on | Status |
|---|---|---|---|
| `/confidence-map` | Akib (fusion logic) + Jeet (serving/GeoJSON) | Susovan's model output | Ready to build |
| `/grid/{id}/timeseries` | Akib | Susovan's model output | Ready to build |
| `/grid/{id}/explanation` | Akib | Susovan's model + SHAP (raw variables) + analog index | Ready to build, without regime_tag |
| `/regimes/current` | Akib | Susovan's regime classifier | Stub only — real work starts once clustering exists |
| `/health` | Jeet | Live ingestion pipeline | Ready to build |

## Remaining action items before Day 2 truly starts
- **Susovan:** confirm the 121×141 grid's lat/lon bounding box
- **Susovan:** confirm/override the canonical variable naming table above
- **Susovan:** train the error/bust-probability model on control-forecast-vs-ERA5 pairs (lead_time_hours, lat, lon, season as conditioning features) — this is now the core Day 2 model, not ensemble-spread-based
- **Akib:** once naming is confirmed, build SHAP wiring against raw variables only, `regime_tag` stays `null`
- **Jeet:** build dashboard to treat grid cells as points/heatmap, not subdivision polygons; treat `/regimes/current` as unavailable for now

## Roadmap (explicitly out of scope for MVP, for the pitch's "future work" section)
- Within-model ensemble spread — requires downloading NCEP TIGGE perturbed members (`pf`)
- Multi-model disagreement (GFS vs ECMWF) — requires a second forecast source, separate ingestion pipeline
- Regime classification / clustering — requires unsupervised clustering step on synoptic fields, not yet built

This version is locked for Day 2 start.


<!-- Updated Domain to 5-35N, 65-100E -->