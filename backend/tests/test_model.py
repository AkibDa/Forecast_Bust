import pytest
import os
import sys
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.shared_utils import get_month_from_dates
from app.explanation import get_explanation
from app.confidence import get_confidence_map
from app.model_interface import predict, predict_batch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def setup_module():
    from app.ingestion import run_ingestion_pipeline
    run_ingestion_pipeline()

def test_month_function_parity():
    # Test month parity train vs inference
    # Inference uses get_month_from_dates(init_time_str, lead_time_hours)
    # Train uses pd.to_datetime(valid_time).dt.month
    import pandas as pd
    valid_time = pd.to_datetime('2026-09-27')
    train_month = valid_time.month
    
    # corresponding init_time for lead_time_hours = 24
    init_time = valid_time - pd.to_timedelta(24, unit='h')
    init_time_str = init_time.isoformat()
    
    infer_month = get_month_from_dates(init_time_str, 24)
    assert train_month == infer_month

def test_shap_sign_vs_direction():
    # Call explanation directly
    resp = get_explanation("22.5_88.25", "2026-09-27", 1)
    drivers = resp.top_drivers
    for d in drivers:
        if d.contribution > 0:
            assert d.direction == "lowers_confidence"
        elif d.contribution < 0:
            assert d.direction == "raises_confidence"

def test_grid_id_validation():
    # Negative grid_id via testclient
    r = client.get("/api/v1/grid/abc/explanation?forecast_date=2026-09-27&lead_day=1")
    assert r.status_code == 422
    assert "error" in r.json()

def test_explanation_determinism():
    r1 = client.get("/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1").json()
    r2 = client.get("/api/v1/grid/22.5_88.25/explanation?forecast_date=2026-09-27&lead_day=1").json()
    
    assert r1["top_drivers"] == r2["top_drivers"]
    assert r1["analogs"] == r2["analogs"]

def test_batch_vs_single_cell_prediction_equality():
    # Single prediction
    # Mock some features
    features = {"lead_time_hours": 24, "latitude": 22.5, "longitude": 88.25, "month": 9, "msl": 101000, "10u": 2.0, "10v": 3.0, "2t": 300.0, "tp": 5.0}
    single_prob = predict(features)["bust_probability"]
    
    # Batch prediction
    import pandas as pd
    df = pd.DataFrame([features])
    batch_prob = predict_batch(df)['bust_probability'].iloc[0]
    
    assert np.isclose(single_prob, batch_prob, atol=1e-5)
