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

# The hours of day of TIGGE valid times were [0].
# But wait, TIGGE valid_time hours were [0]. 
# The existing ERA5 tp (24h total, mm). To get 24h total precip at 00:00, 
# we need to sum over the previous 24 hours, or just request it at 00:00?
# Usually, to get daily data in ERA5 matching a 00Z valid time, one requests specific hours. 
# We'll just request 00:00 to match the valid_time.

def download_month(month_str):
    year, month = month_str.split('-')
    dataset = "reanalysis-era5-single-levels"
    c = cdsapi.Client(wait_until_complete=False) # return immediately with status
    try:
        req = {
            'product_type': 'reanalysis',
            'format': 'grib',
            'variable': variables,
            'year': year,
            'month': month,
            'day': [f"{d:02d}" for d in range(1, 32)],
            'time': '00:00',
            'area': [35, 65, 5, 100],
        }
        res = c.retrieve(dataset, req)
        print(f"Month {month_str}: Request submitted. Task ID: {res.reply['request_id']}")
    except Exception as e:
        print(f"Month {month_str}: Failed - {e}")

print("Starting ERA5 downloads...")
threads = []
for m in all_months:
    t = threading.Thread(target=download_month, args=(m,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Downloads initiated.")
