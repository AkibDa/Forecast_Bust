import cdsapi
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# We check status of the most recent requests. Since I resubmitted them in the previous turn,
# I will fetch the request list and show the status of the 24 most recent.
print("--- 1. CDS Request Status ---")
try:
    c = cdsapi.Client(wait_until_complete=False)
    # The new cdsapi may not have a simple list function, but we can look at the dashboard 
    # or just fetch the tasks if there's an API.
    # Actually, we can just print a message that the API is tracking them, or we can use the requests library 
    # to query the CDS API if needed.
    
    # We will simulate the check or if `c` has a requests property:
    # We don't have an easy way to list all requests without knowing their UUIDs unless we hit the API directly.
    import requests
    url = c.url + "/tasks"
    auth = (c.key.split(':')[0], c.key.split(':')[1])
    res = requests.get(url, auth=auth, verify=False).json()
    
    # The API returns a list or dict of tasks. Let's see what's in res.
    if isinstance(res, list):
        tasks = res[:24]
        for t in tasks:
            print(f"Task ID: {t.get('request_id')} - Status: {t.get('state')}")
    else:
        print("Could not retrieve tasks directly, please check CDS dashboard.")
except Exception as e:
    print(f"Error checking CDS status: {e}")

print("\n--- Month Boundary Logic ---")
print("Implementation note: When ERA5 is downloaded, we will concatenate all monthly DataFrames")
print("into a single DataFrame before applying compute_tp_truth(), and then drop 2023-01-01.")
