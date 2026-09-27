import numpy as np
from typing import List, Optional
from pydantic import BaseModel
from sklearn.neighbors import NearestNeighbors

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

# --- Task 2: Mock Historical Analog Retrieval System ---
# Create a searchable archive of mock historical ERA5 embeddings.
# Variables: t2m, msl, u10, v10, tp -> flattened/downsampled/PCA'd

NUM_HISTORICAL_CASES = 100
historical_dates = [f"2023-{np.random.randint(1,13):02d}-{np.random.randint(1,28):02d}" for _ in range(NUM_HISTORICAL_CASES)]
historical_events = [f"Historical Weather Event {i}" for i in range(NUM_HISTORICAL_CASES)]

# Create some random embeddings for these historical cases (e.g., 32-dim)
historical_embeddings = np.random.rand(NUM_HISTORICAL_CASES, 32)

# Build a nearest neighbor index
nn_model = NearestNeighbors(n_neighbors=3, metric='cosine')
nn_model.fit(historical_embeddings)

def get_explanation(grid_id: str, forecast_date: str, lead_day: int) -> ExplanationResponse:
    # 1. Analog Retrieval
    # Simulate an embedding of today's forecast to query the nearest neighbors index
    query_embedding = np.random.rand(1, 32)
    distances, indices = nn_model.kneighbors(query_embedding)
    
    analogs = []
    for rank, idx in enumerate(indices[0]):
        # Convert cosine distance to a mock similarity score [0, 1]
        similarity = round(max(0.0, 1.0 - distances[0][rank]), 2)
        analogs.append(Analog(
            case_date=historical_dates[idx],
            event_name=historical_events[idx],
            similarity_score=similarity,
            historical_error_summary=f"Historical forecast bust of magnitude {round(np.random.uniform(5, 45), 1)}"
        ))

    # 2. Mock SHAP Feature Contributions
    # Only using canonical raw variable names: t2m, mslp, u10, v10, precip
    canonical_features = ['t2m', 'mslp', 'u10', 'v10', 'precip']
    np.random.shuffle(canonical_features)
    
    top_drivers = []
    # Pick the top 3 features as drivers for this mock
    for feat in canonical_features[:3]:
        contrib = round(np.random.uniform(0.1, 0.6) * np.random.choice([1, -1]), 2)
        direction = "raises_confidence" if contrib > 0 else "lowers_confidence"
        top_drivers.append(Driver(
            feature=feat,
            contribution=abs(contrib),
            direction=direction
        ))

    return ExplanationResponse(
        grid_id=grid_id,
        lead_day=lead_day,
        regime_tag=None, # Explicitly out of scope
        top_drivers=top_drivers,
        analogs=analogs
    )
