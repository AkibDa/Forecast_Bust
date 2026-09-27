from pydantic import BaseModel
from typing import Optional
from .ingestion import get_ingestion_status

class HealthResponse(BaseModel):
    status: str
    model_version: str
    last_ingestion: Optional[str]
    ingestion_status: str

def get_health() -> HealthResponse:
    ingestion_info = get_ingestion_status()
    
    return HealthResponse(
        status="ok",
        model_version="v1",
        last_ingestion=ingestion_info["last_success_time"],
        ingestion_status=ingestion_info["last_status"]
    )
