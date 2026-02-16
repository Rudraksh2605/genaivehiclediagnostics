"""
Predictive Analytics API routes.
Provides endpoints for battery/tire predictions and driving score.
"""

from fastapi import APIRouter
from backend.services.data_store import DataStore
from backend.analytics.predictive_engine import generate_predictive_report

router = APIRouter(prefix="/predictive", tags=["Predictive Analytics"])


@router.get("/analysis")
async def get_predictive_analysis():
    """Return full predictive analytics report (predictions + driving score)."""
    store = DataStore()
    report = generate_predictive_report(store)

    predictions = []
    for p in report.predictions:
        predictions.append({
            "signal": p.signal,
            "type": p.prediction_type,
            "current_value": round(p.current_value, 2),
            "predicted_value": round(p.predicted_value, 2),
            "confidence": round(p.confidence, 2),
            "time_horizon_seconds": p.time_horizon_seconds,
            "message": p.message,
            "severity": p.severity,
        })

    driving_score = None
    if report.driving_score:
        ds = report.driving_score
        driving_score = {
            "overall": round(ds.overall_score, 1),
            "speed": round(ds.speed_score, 1),
            "braking": round(ds.braking_score, 1),
            "efficiency": round(ds.efficiency_score, 1),
        }

    return {
        "predictions": predictions,
        "driving_score": driving_score,
        "data_points": report.data_points_analyzed,
        "timestamp": report.timestamp,
    }
