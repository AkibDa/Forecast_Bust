import pytest
from fastapi.testclient import TestClient
from app.main import app
import pandas as pd
import numpy as np

client = TestClient(app)

def setup_module():
    from app.ingestion import run_ingestion_pipeline
    run_ingestion_pipeline()
    from app.model_interface import _load_model
    _load_model()

def test_month_function_parity():
    from app.shared_utils import get_month_from_dates
    valid_time = pd.to_datetime('2026-09-27')
    train_month = valid_time.month
    init_time = valid_time - pd.to_timedelta(24, unit='h')
    infer_month = get_month_from_dates(init_time.isoformat(), 24)
    assert train_month == infer_month

def test_shap_sign_vs_direction():
    from app.explanation import get_explanation
    resp = get_explanation("22.5_88.25", "2026-09-27", 1)
    for d in resp.top_drivers:
        if d.contribution > 0:
            assert d.direction == "lowers_confidence"
        elif d.contribution < 0:
            assert d.direction == "raises_confidence"

def test_grid_id_validation():
    r = client.get("/api/v1/grid/abc/explanation?forecast_date=2026-09-27&lead_day=1")
    assert r.status_code == 422

def test_explanation_determinism():
    r1 = client.get("/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1").json()
    r2 = client.get("/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1").json()
    assert r1["top_drivers"] == r2["top_drivers"]

def test_batch_vs_single_cell_prediction_equality():
    from app.model_interface import predict, predict_batch
    features = {"lead_time_hours": 24, "latitude": 22.5, "longitude": 88.25, "month": 9, "msl": 101000, "10u": 2.0, "10v": 3.0, "2t": 300.0, "tp": 5.0}
    single_prob = predict(features)["bust_probability"]
    df = pd.DataFrame([features])
    batch_prob = predict_batch(df)['bust_probability'].iloc[0]
    assert np.isclose(single_prob, batch_prob, atol=1e-5)

def test_out_of_domain_grid_id():
    r = client.get("/api/v1/grid/99_200/timeseries?forecast_date=2026-09-27")
    assert r.status_code == 422

def test_malformed_date():
    r = client.get("/api/v1/confidence-map?forecast_date=2026-13-45&lead_day=1")
    assert r.status_code == 422
