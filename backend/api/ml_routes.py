"""
ML Training and Prediction API Routes (Scikit-Learn Backend).

Provides endpoints for:
  - POST /ml/train — Train ML models (RandomForest/IsolationForest) on CPU
  - GET  /ml/predict — Run inference on current vehicle data
  - GET  /ml/status — Get training status
"""

import logging
import threading
from fastapi import APIRouter, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


# ── Training Endpoint ────────────────────────────────────────────────────────

@router.post("/train")
async def train_models(
    num_sequences: int = 2000,
):
    """
    Train all ML models (battery predictor, tire wear detector, anomaly detector).
    
    Uses Scikit-Learn on CPU (fast and efficient).
    Training runs in a background thread to avoid blocking the API.
    """
    from backend.ml.ml_trainer import get_trainer

    trainer = get_trainer()

    if trainer.training_status["status"] == "training":
        raise HTTPException(
            status_code=409,
            detail="Training already in progress",
        )

    def _train_background():
        try:
            results = trainer.train_all_models(
                num_sequences=num_sequences,
            )
            logger.info(f"Training completed: {results}")
            # Reload predictor models
            from backend.ml.ml_predictor import get_predictor
            get_predictor().reload_models()
        except Exception as e:
            logger.error(f"Training failed: {e}")
            trainer._training_status["status"] = "failed"
            trainer._training_status["error"] = str(e)

    thread = threading.Thread(target=_train_background, daemon=True)
    thread.start()

    return {
        "message": "Training started in background (Scikit-Learn CPU)",
        "config": {
            "num_sequences": num_sequences,
            "backend": "scikit-learn",
            "models": ["RandomForestRegressor", "IsolationForest"]
        }
    }


# ── Training Status ──────────────────────────────────────────────────────────

@router.get("/status")
async def get_training_status():
    """Get current training status and progress."""
    from backend.ml.ml_trainer import get_trainer

    trainer = get_trainer()
    return trainer.training_status


# ── Prediction Endpoint ──────────────────────────────────────────────────────

@router.post("/predict")
async def predict_from_current_data():
    """
    Run ML inference on the current vehicle telemetry data.
    
    Returns predictions from all trained models:
    - Battery depletion time (RandomForest)
    - Tire wear score (RandomForest)
    - Anomaly detection (IsolationForest)
    """
    from backend.ml.ml_predictor import get_predictor
    from backend.services.data_store import DataStore

    predictor = get_predictor()
    store = DataStore()

    if not predictor.is_ready:
        return {
            "ml_models_available": False,
            "message": "No trained models — call POST /ml/train first",
            "battery_prediction": {"available": False},
            "tire_prediction": {"available": False},
            "anomaly_detection": {"available": False},
        }

    # Get current vehicle data
    # Access Pydantic model directly
    telemetry = store.telemetry.dict() if hasattr(store.telemetry, "dict") else store.telemetry.__dict__

    vehicle_data = {
        "speed": telemetry.get("speed", 60),
        "battery_soc": telemetry.get("battery", {}).get("soc", 80),
        "battery_voltage": telemetry.get("battery", {}).get("voltage", 380),
        "battery_temp": telemetry.get("battery", {}).get("temperature", 25),
        "tire_pressure": telemetry.get("tires", {}), # direct access if dict
        "throttle_position": telemetry.get("throttle_position", 50),
        "brake_position": telemetry.get("brake_position", 0),
        "ev_range": telemetry.get("ev_range", 200),
    }

    # Handle nested tire pressure if needed
    t = vehicle_data["tire_pressure"]
    if not isinstance(t, dict):
         # If it's a TireStatus object
         t = t.dict() if hasattr(t, "dict") else t.__dict__
    
    vehicle_data["tire_pressure"] = t

    return predictor.predict_all(vehicle_data)


# ── Backend Info ─────────────────────────────────────────────────────────────

@router.get("/info")
async def get_backend_info():
    """Get ML backend information."""
    import sklearn
    import pandas
    return {
        "backend": "scikit-learn",
        "sklearn_version": sklearn.__version__,
        "pandas_version": pandas.__version__,
        "device": "cpu",
        "description": "Efficient CPU-based training using RandomForest and IsolationForest"
    }
