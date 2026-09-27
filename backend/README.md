# Backend for Forecast Bust Detection

This is a FastAPI backend serving mock data conforming strictly to the `v1` API contract.

## How to run
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Where to implement logic

- **Akib**: Implement your fusion layer in `app/confidence.py` and SHAP/explanation endpoints in `app/explanation.py`. The `app/model_interface.py` is ready for you to call Susovan's model.
- **Susovan**: Provide the implementation in `app/model_interface.py`. Ensure your output matches the expected Pydantic shape.
- **Jeet**: Start adding the real data ingestion pipelines in `app/ingestion.py`. You also own the `app/health.py` endpoint.
