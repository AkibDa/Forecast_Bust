# Forecast Bust Detection - MVP

This project is an AI-based forecast bust detection system for medium-range weather forecasts, designed to predict historical forecast error using control forecast fields versus ERA5 truth. This MVP is built for the SIH 2026 hackathon, focusing on providing actionable confidence signals and feature-level drivers.

## How to Run End-to-End

### 1. Start the Backend (FastAPI)
Open a terminal and run:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be available at `http://localhost:8000`. You can test it via `http://localhost:8000/api/v1/health`.

### 2. Start the Frontend (React + Vite)
Open a second terminal and run:
```bash
cd frontend
npm install
npm run dev
```
The dashboard will be available at `http://localhost:5173`.

## Team Roles & Ownership

Please edit your respective modules to replace the mock data with actual implementation:

- **Akib (Fusion Layer & Explainability)**
  - Owns: `backend/app/confidence.py`, `backend/app/explanation.py`
  - Needs to wire the SHAP explainer against Susovan's model and the analog retrieval logic.
- **Susovan (Core Model)**
  - Owns: `backend/app/model_interface.py`
  - Needs to implement the core ML model that predicts `confidence_score` and `bust_probability` and define the 121×141 bounding box.
- **Jeet (Dashboard & Ingestion)**
  - Owns: `frontend/` and `backend/app/ingestion.py`, `backend/app/health.py`
  - Needs to enhance the React dashboard visually and build the data pipelines.

**Note:** The API contract serves as the source of truth for the system's schema and structure. Check `/docs/api_contract_v1.md`.