from typing import List, Optional
from pydantic import BaseModel

class Driver(BaseModel):
    feature: str
    contribution: float
    direction: str

class Analog(BaseModel):
    case_date: str
    event_name: str
    similarity_score: float
    historical_error_summary: str

class ExplanationResponse(BaseModel):
    grid_id: str
    lead_day: int
    regime_tag: Optional[str] = None
    top_drivers: List[Driver]
    analogs: List[Analog]

def get_explanation(grid_id: str, forecast_date: str, lead_day: int) -> ExplanationResponse:
    # Stub data matching the contract exactly
    return ExplanationResponse(
        grid_id=grid_id,
        lead_day=lead_day,
        regime_tag=None,
        top_drivers=[
            Driver(feature="mslp", contribution=0.31, direction="lowers_confidence"),
            Driver(feature="precipitation", contribution=0.18, direction="lowers_confidence"),
            Driver(feature="u10", contribution=-0.12, direction="raises_confidence")
        ],
        analogs=[
            Analog(
                case_date="2021-07-18",
                event_name="Uttarakhand rainfall bust",
                similarity_score=0.87,
                historical_error_summary="Day-3 rainfall forecast under-predicted by 40mm+; observed bust"
            )
        ]
    )
