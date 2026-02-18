"""
Telemetry History API routes.
Provides historical telemetry data for trend charting and analytics.
"""

from fastapi import APIRouter, Query
from typing import Any, Dict

from backend.services.data_store import DataStore

router = APIRouter(prefix="/vehicle", tags=["Telemetry History"])


@router.get("/history", summary="Get telemetry history for trend charts")
async def get_telemetry_history(
    limit: int = Query(default=60, ge=1, le=300, description="Number of data points")
) -> Dict[str, Any]:
    """
    Return recent telemetry snapshots for time-series visualization.
    Each snapshot includes speed, battery SoC, tire pressures, etc.
    Max 300 data points (5 minutes at 1Hz).
    """
    store = DataStore()
    history = store.get_telemetry_history(limit)
    return {
        "count": len(history),
        "history": history,
    }
