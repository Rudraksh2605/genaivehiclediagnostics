import requests
import time

API_BASE = "http://localhost:8000"

python_code = """
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/ota-dynamic-test", tags=["Dynamic OTA"])

_alerts: List[Dict[str, str]] = []

@router.get("/status")
async def get_status():
    return {"message": "I am a dynamically hot-loaded endpoint!", "alerts": _alerts}

def process_telemetry(telemetry_data: dict, store: object) -> None:
    # Trigger a fake alert if speed goes above 50
    speed = telemetry_data.get("speed", 0)
    if speed > 50:
        _alerts.append({"msg": f"Speed {speed} exceeds OTA limit!", "ts": telemetry_data.get("timestamp")})
    
    # Keep only the last 5
    if len(_alerts) > 5:
        _alerts.pop(0)
"""

print("1. Sending OTA Deploy request...")
res = requests.post(
    f"{API_BASE}/ota/deploy",
    json={
        "update_type": "code_module",
        "description": "Test dynamic python hotloading",
        "payload": {
            "module_name": "speed_limiter_module",
            "language": "python",
            "code": python_code
        }
    }
)

print(f"Deploy Response: {res.status_code}")
print(res.json())

print("\n2. Starting the simulator so telemetry hooks fire...")
requests.post(f"{API_BASE}/vehicle/simulate/start?variant=EV")

print("Waiting 3 seconds for telemetry to tick...")
time.sleep(3)

print("\n3. Testing the dynamically mounted REST endpoint: GET /ota-dynamic-test/status")
try:
    dyn_res = requests.get(f"{API_BASE}/ota-dynamic-test/status")
    print(f"Endpoint HTTP Status: {dyn_res.status_code}")
    print(dyn_res.json())
except Exception as e:
    print(f"Failed to reach endpoint: {e}")

print("\n4. Stopping simulator...")
requests.post(f"{API_BASE}/vehicle/simulate/stop")
