import os
import cdsapi
import threading

months_2023 = [f"2023-{m:02d}" for m in range(1, 13)]
months_2024 = [f"2024-{m:02d}" for m in range(1, 13)]
all_months = months_2023 + months_2024

variables = [
    '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature',
    '2m_temperature', 'mean_sea_level_pressure', 'surface_pressure',
    'sea_surface_temperature', 'total_precipitation'
]

# We want 24 hourly steps to compute daily tp sums correctly
times = [f"{h:02d}:00" for h in range(24)]

def print_and_submit_month(month_str):
    year, month = month_str.split('-')
    dataset = "reanalysis-era5-single-levels"
    c = cdsapi.Client(wait_until_complete=False)
    
    req = {
        'product_type': 'reanalysis',
        'format': 'grib',
        'variable': variables,
        'year': year,
        'month': month,
        'day': [f"{d:02d}" for d in range(1, 32)],
        'time': times,
        'area': [35, 65, 5, 100],
        'grid': [0.5, 0.5]
    }
    
    if month_str == '2023-01':
        print("\n--- 2. Submitted CDS request body (example) ---")
        import json
        print(json.dumps(req, indent=2))
        
    try:
        res = c.retrieve(dataset, req)
        if month_str == '2023-01':
            print(f"Resubmitted {month_str}: Task ID: {res.reply['request_id']}")
    except Exception as e:
        if month_str == '2023-01':
            print(f"Failed {month_str} - {e}")

threads = []
for m in all_months:
    t = threading.Thread(target=print_and_submit_month, args=(m,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("\nAll corrected CDS requests resubmitted.")
