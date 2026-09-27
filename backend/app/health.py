from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    model_version: str
    last_ingestion: str

def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_version="v1",
        last_ingestion="2026-09-26T06:00:00Z"
    )
