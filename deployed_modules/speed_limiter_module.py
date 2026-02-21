
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
