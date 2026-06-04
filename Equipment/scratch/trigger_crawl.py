import httpx
import time

url = "http://localhost:8000/api/crawl/discover-manufacturers"
params = {
    "equipment_master_id": 8,  # Pump is ID 8
    "no_cache": True
}

try:
    print(f"Triggering manufacturer discovery for Pump (ID 8)...")
    res = httpx.post(url, params=params, timeout=10)
    print("Response:", res.status_code, res.json())
    
    # Poll status
    status_url = "http://localhost:8000/api/crawl/status"
    for _ in range(30):
        time.sleep(2)
        s_res = httpx.get(status_url)
        status = s_res.json()
        print(f"Stage: {status.get('stage')}, Percent: {status.get('percent')}%, Msg: {status.get('status_msg')}")
        if not status.get("active"):
            print("Crawl completed! Final status details:")
            print(status)
            break
except Exception as e:
    print("Error:", e)
