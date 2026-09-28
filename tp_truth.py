import pandas as pd
import unittest

def compute_tp_truth(era5_hourly_df: pd.DataFrame, valid_time: str) -> pd.DataFrame:
    """
    Computes daily total precipitation (in mm) for a specific valid_time.
    tp truth = sum of the 24 hourly steps ending at valid_time (inclusive of the 00:00 step of valid_time, 
    and the 23 steps prior).
    
    Expected era5_hourly_df columns: ['valid_time', 'latitude', 'longitude', 'tp']
    where 'tp' is in meters.
    
    Returns: DataFrame with ['valid_time', 'latitude', 'longitude', 'tp_mm']
    """
    vt = pd.to_datetime(valid_time)
    start_time = vt - pd.to_timedelta(23, unit='h')
    
    # Filter to the 24-hour window
    mask = (era5_hourly_df['valid_time'] >= start_time) & (era5_hourly_df['valid_time'] <= vt)
    window_df = era5_hourly_df[mask].copy()
    
    # Convert meters to mm
    window_df['tp_mm'] = window_df['tp'] * 1000.0
    
    # Sum over the 24 hourly steps per grid cell
    daily_tp = window_df.groupby(['latitude', 'longitude'])['tp_mm'].sum().reset_index()
    daily_tp['valid_time'] = vt
    return daily_tp[['valid_time', 'latitude', 'longitude', 'tp_mm']]

class TestTpTruth(unittest.TestCase):
    def test_compute_tp_truth(self):
        # Create mock hourly data for one cell
        dates = pd.date_range(start='2023-01-01 01:00', end='2023-01-02 00:00', freq='h')
        # 24 hours of 0.001 meters = 1 mm each hour -> Total 24 mm
        df = pd.DataFrame({
            'valid_time': dates,
            'latitude': [35.0] * 24,
            'longitude': [65.0] * 24,
            'tp': [0.001] * 24
        })
        
        # Add some data outside the window to ensure it's filtered
        df.loc[24] = ['2023-01-02 01:00', 35.0, 65.0, 1.0] # Should be ignored
        df['valid_time'] = pd.to_datetime(df['valid_time'])
        
        res = compute_tp_truth(df, '2023-01-02 00:00:00')
        
        self.assertEqual(len(res), 1)
        self.assertEqual(res.iloc[0]['tp_mm'], 24.0)
        self.assertEqual(res.iloc[0]['valid_time'], pd.to_datetime('2023-01-02 00:00:00'))

if __name__ == '__main__':
    print("\n--- 3. tp truth function and unit test ---")
    unittest.main(verbosity=2)
