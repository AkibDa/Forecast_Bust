import random
from typing import Dict

def predict(lat: float, lon: float, forecast_date: str, lead_day: int) -> Dict[str, float]:
    """
    Interface for Susovan's model.
    Returns: { "confidence_score": float, "bust_probability": float }
    """
    # Stub: return random but plausible values
    confidence_score = round(random.uniform(0.3, 0.95), 2)
    bust_probability = round(1.0 - confidence_score, 2)
    return {
        "confidence_score": confidence_score,
        "bust_probability": bust_probability
    }
