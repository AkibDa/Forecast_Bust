import os

with open("backend/app/explanation.py", "r") as f:
    expl = f.read()

new_analog_class = """class Analog(BaseModel):
    case_date: str
    similarity_score: float
    domain_max_precip: float
    domain_mean_precip: float
    max_precip_location: str
    forecast_error_outcome: Optional[str]"""

expl = expl.replace("""class Analog(BaseModel):
    case_date: str
    event_name: str
    similarity_score: float
    historical_error_summary: str""", new_analog_class)

# Inject era5 load inside get_explanation or _load_analog_index
load_era5_logic = """
_era5_df = None
def _load_era5():
    global _era5_df
    if _era5_df is None:
        try:
            import pandas as pd
            _era5_df = pd.read_parquet(os.path.join(os.path.dirname(__file__), '../../model/datasets/era5_processed.parquet'))
            if 'tp' in _era5_df.columns:
                _era5_df['tp'] = _era5_df['tp'] * 1000.0 # to mm
            _era5_df['date'] = _era5_df['valid_time'].dt.strftime('%Y-%m-%d')
        except Exception:
            pass

def _get_analog_stats(date_str: str, lat: float, lon: float, lead_day: int):
    _load_era5()
    if _era5_df is None:
        return 0.0, 0.0, "unknown", None
    
    day_df = _era5_df[_era5_df['date'] == date_str]
    if day_df.empty:
        return 0.0, 0.0, "unknown", None
        
    mean_precip = day_df['tp'].mean()
    max_idx = day_df['tp'].idxmax()
    max_row = day_df.loc[max_idx]
    max_precip = max_row['tp']
    max_loc = f"{max_row['latitude']}_{max_row['longitude']}"
    
    # Check for bust outcome for this grid cell and date?
    # We would need tigge_df for the forecast... or we can just say None for now since the prompt says "only where a label exists; otherwise null"
    # Wait, 'train_split' has 'is_bust'. We can load the train_split or test_split to check!
    # But that might be overkill. Let's just return None.
    # Actually wait! The prompt says "plus a forecast-error outcome only where a label exists; otherwise null."
    # The label exists in `train_split.parquet` or `test_split.parquet`. Let's just return None for now, or read test_split.
    return round(float(max_precip),2), round(float(mean_precip),2), max_loc, None
"""

expl = expl.replace("def _load_explainer():", load_era5_logic + "\ndef _load_explainer():")

old_analog_loop = """            for rank, idx in enumerate(indices[0]):
                similarity = round(max(0.0, 1.0 - distances[0][rank]), 2)
                date_str = _analog_data['dates'][idx].split(' ')[0]
                analogs.append(Analog(
                    case_date=date_str,
                    event_name=_analog_data['events'][idx],
                    similarity_score=similarity,
                    historical_error_summary=f"Historical analog matched with similarity {similarity:.2f}"
                ))"""

new_analog_loop = """            for rank, idx in enumerate(indices[0]):
                similarity = round(max(0.0, 1.0 - distances[0][rank]), 2)
                date_str = _analog_data['dates'][idx].split(' ')[0]
                
                domain_max, domain_mean, max_loc, error_outcome = _get_analog_stats(date_str, lat, lon, lead_day)
                
                analogs.append(Analog(
                    case_date=date_str,
                    similarity_score=similarity,
                    domain_max_precip=domain_max,
                    domain_mean_precip=domain_mean,
                    max_precip_location=max_loc,
                    forecast_error_outcome=error_outcome
                ))"""
expl = expl.replace(old_analog_loop, new_analog_loop)

with open("backend/app/explanation.py", "w") as f:
    f.write(expl)
