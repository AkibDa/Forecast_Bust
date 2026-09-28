# System Status & Handoff — Forecast Bust Detection MVP
**As of:** 28 Sep 2026 | **SIH idea PPT due:** 30 Sep 2026

## 1. One-paragraph honest summary
The end-to-end pipeline works: live GFS ingestion, a versioned API with a strict error contract, a calibrated model, SHAP explanations, analog retrieval, and a dashboard. **The model has no demonstrated predictive skill, and no accuracy metric reported so far is valid for external claims.** Its outputs are currently near-uniform (live-day mean bust probability about 0.003). The ERA5 truth data needed to train and validate properly is still downloading, and that download is unverified.

Status labels used below: **WORKS**, **WORKS (caveat)**, **FALLBACK**, **NOT BUILT**, **INVALID**, **UNVERIFIED**.

## 2. Component status

| Component | Status | Notes / evidence |
|---|---|---|
| API contract and error format | WORKS | `{"error":{"code","message"}}` on all errors; negative tests pass (bad grid_id, out-of-domain, bad date, lead_day 0/11); 7 pytest tests (month parity, SHAP sign, grid_id, determinism, batch vs single, out-of-domain, malformed date). New code (lag features, retrain script) has no tests yet. |
| Domain / grid | WORKS (caveat) | 5–35°N, 65–100°E, 0.5°, 61×71 = 4,331 cells, from `config.DOMAIN`. TIGGE confirmed at 0.5°. The existing ERA5 file (2025-01-01 to 2026-09-19) is a different, 0.25° (121×141) grid. Live GFS is 0.25° subsampled to 0.5°. UNVERIFIED: that the subsampling picks exact grid nodes. |
| Live ingestion | WORKS (caveat) | GFS f024 pulled from NOMADS (4 h publish-lag offset), plus f048 of the previous cycle for lag features. **Day 1 only**; Days 2–10 return 422 with `supported_lead_days`. Requires a successful startup pull. |
| GRIB cache | FALLBACK | Backup at `model/datasets/backup/gfs_cached_demo.grb2` (regenerated from a fresh pull on 28 Sep). `/health` reports `mode="cache"`. UNVERIFIED: that responses label the cached cycle's date instead of passing it off as the requested date. |
| Climatology fallback | FALLBACK | Default OFF (`ALLOW_CLIMATOLOGY_FALLBACK`). If enabled, values are historical climatology, not a forecast. **Must be OFF for any demo.** |
| Precipitation handling | WORKS (caveat) | Historical TIGGE: 24 h differencing (lead 24 uses the accumulated value as-is). Live GFS: 0–24 h stepRange, asserted. ERA5 truth = sum of 24 hourly steps ending at `valid_time`, in mm, unit-tested **on synthetic input only**; not yet run on real downloaded ERA5. |
| Lagged disagreement (`lag_diff`) | UNVERIFIED | Code exists. The training table has 1,886,976 rows; the expected count is about 28.5 M (730 inits × 9 leads × 4,331 cells) and the row count is not a multiple of 4,331. The claim that nothing was dropped contradicts this. The "max row" previously reported was an approximation, not real output. Max `lag_diff_tp` of 546 mm exceeds the largest 24 h TIGGE total seen (248 mm), so accumulated-vs-24 h mixing is possible. |
| Model weights (`calibrated_xgb.pkl`) | INVALID | Provenance unclear: it is either the model trained on the 10-day overlap or a later proxy-label dry run. Neither shows skill. Outputs are degenerate: live and historical maps show mean bust probability of about 0.003, p90 about 0.006, nearly all cells at the lowest calibration step. |
| Earlier reported metrics | INVALID | The AUC of 0.91 and 0.72, the precision/recall, and the backtest events (all 7–10 Jan 2025) came from **10 verification days** (1–10 Jan 2025; 7/2/1 init dates in train/calib/test). Z-scores used groups of 1–10 samples computed on all data before the split (leakage, unstable). **Do not cite.** |
| Proxy-label dry run | INVALID | AUC 0.487 (below the [lead, lat, lon, month] baseline of 0.623), Brier 0.152 (a constant prediction scores about 0.106), Oct–Dec per-month AUC below 0.5. Shows no skill. |
| SHAP explanations | WORKS (caveat) | Real `TreeExplainer` on the base XGBoost; positive SHAP on the bust class = `lowers_confidence` (tested). Explains an unvalidated model. UNVERIFIED: which base estimator of the `CalibratedClassifierCV` ensemble is used. Values are in log-odds space. |
| Analog retrieval | WORKS (caveat) | Real PCA + nearest-neighbour index over 627 ERA5 days (2025-01-01 to 2026-09-19). **Known issues:** that ERA5 file holds hourly-step tp (about 1/24 of daily totals), while the live query is a 24 h total in mm, so the scales don't match; the index grid may not match the 0.5° query; no realized bust outcomes are attached (`forecast_error_outcome` is null); "domain max/mean precip" on the analog cards is not a daily total. Treat analog cards as illustrative. |
| Regime classification | NOT BUILT | `regime_tag` is null; `/regimes/current` returns 501. |
| Ensemble spread, MJO, CAPE | NOT BUILT | TIGGE data is control-forecast only. Lagged disagreement is a substitute, not equivalent. |
| Frontend | UNVERIFIED | Confidence overlay never visually confirmed in a screenshot. Needs bounds 5–35°N, 65–100°E; slider positions for unsupported live days disabled; handling of error bodies; a relative or percentile colour scale (low base rates look flat on a linear scale). |
| ERA5 2023–2024 download | UNVERIFIED | 24 monthly requests (0.5°, 24 hourly steps, area 35/65/5/100) reported submitted after a correction. The agent's status check errored; verify on the CDS "Your requests" page and cancel any earlier wrong-format requests. |
| Existing ERA5 file (2025–2026) | INVALID as daily truth | Stores one hourly-step value per day (about 1/24 of TIGGE's daily total on all 10 overlap days). Anything derived from it (old labels, analog index, analog card facts) is affected. |

## 3. What the pitch may and may not claim

**Safe to claim**
- Working end-to-end prototype: live GFS ingestion, versioned API, dashboard, SHAP + analog explainability.
- A validation design: time-blocked CV, Brier skill score vs constant base rate, reliability diagrams.
- Lagged-forecast disagreement as a spread proxy (Phase 1); ensembles, regimes, multi-model as roadmap.

**Do NOT claim**
- Any AUC, accuracy, precision or recall number.
- "Detected real bust events."
- Regime classification, ensemble spread, MJO/CAPE features.
- A live 10-day forecast (live is Day 1 only).
- That analog outcomes or analog precipitation figures are validated.
- Label screenshots "prototype interface", not "model output".

## 4. Retrain plan when ERA5 arrives (with gates)
1. **Sanity gate:** domain-mean daily tp for ERA5 vs TIGGE on the same days should be within the same order of magnitude (ratio near 1, not 1/24). Join months before windowing; drop 2023-01-01.
2. **Merge** on `(init_time, lead_time_hours, lat, lon)` with ERA5 matched via `valid_time`; assert no duplicate keys.
3. **Labels:** z-scores per `(cell, lead, month ±15 days)` from the training period only, at least 20 samples else a per-lead fallback; print bust rate by month (target about 10%).
4. **Splits:** train 2023; calibrate on blocked out-of-fold predictions (10-day blocks, 10-day embargo) covering all seasons; test Jul–Dec 2024 with embargo.
5. **Features:** base fields + lead + season + `lag_diff`; ablation vs `[lead, lat, lon, month]` baseline.
6. **Report gate:** report only if Brier skill vs constant base rate is above 0 and AUC beats the baseline on the test set. Otherwise record "no demonstrated skill".
7. **Provenance:** store a model card beside the weights (training range, label definition, split dates, metrics, git commit) and expose it in `/health`.
8. **Analog index:** rebuild from 24 h tp totals + msl anomaly at 0.5°, refit scaler/PCA, attach realized bust outcomes; until then, label the analog cards illustrative.
9. **Re-verify** the live-day mean probability is about the base rate, not about 0.

## 5. Open verification list
- [ ] `lag_diff` row count discrepancy explained (and max row printed from real data)
- [ ] Which weights file is deployed, and how it was trained
- [ ] CDS requests: status per month, old requests cancelled
- [ ] Live 0.25° to 0.5° subsampling picks exact nodes
- [ ] Cache mode labels the cached cycle honestly
- [ ] SHAP base-estimator choice
- [ ] Map overlay renders in the browser (screenshot)
- [ ] Number of cells the map endpoint serves (4,331 or downsampled)
- [ ] Tests exist for lag features, tp truth on real data, and the retrain merge
