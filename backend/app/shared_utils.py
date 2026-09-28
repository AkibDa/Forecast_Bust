import pandas as pd
from datetime import datetime

def get_month_from_dates(init_time: str | datetime, lead_time_hours: int) -> int:
    """
    Computes the month based on valid_time (init_time + lead_time_hours).
    This matches the training definition where valid_time month is used.
    """
    init_dt = pd.to_datetime(init_time)
    valid_time = init_dt + pd.Timedelta(hours=lead_time_hours)
    return valid_time.month
