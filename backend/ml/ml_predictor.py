"""
ML Predictor for Vehicle Diagnostics (Scikit-Learn Version).

Loads trained RandomForest/IsolationForest models and runs inference.
Replaced TensorFlow implementation for better portability and CPU performance.
"""

import logging
import os
import joblib
from typing import Dict, Any, Optional, List

import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")


class VehicleMLPredictor:
    """Runs inference using trained Scikit-Learn models."""

    def __init__(self):
        self._battery_model = None
        self._tire_model = None
        self._anomaly_model = None
        self._models_loaded = False
        self._load_models()

    def _load_models(self):
        """Load all trained models from disk."""
        try:
            bat_path = os.path.join(MODELS_DIR, "battery_predictor.joblib")
            tire_path = os.path.join(MODELS_DIR, "tire_wear_detector.joblib")
            anom_path = os.path.join(MODELS_DIR, "anomaly_detector.joblib")

            if os.path.exists(bat_path):
                self._battery_model = joblib.load(bat_path)
                logger.info("Battery predictor (RF) loaded")

            if os.path.exists(tire_path):
                self._tire_model = joblib.load(tire_path)
                logger.info("Tire wear detector (RF) loaded")

            if os.path.exists(anom_path):
                self._anomaly_model = joblib.load(anom_path)
                logger.info("Anomaly detector (IF) loaded")

            self._models_loaded = any([
                self._battery_model,
                self._tire_model,
                self._anomaly_model,
            ])
            
            if self._models_loaded:
                logger.info("ML models loaded successfully")
            else:
                logger.info("No trained models found - call POST /ml/train first")

        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")
            self._models_loaded = False

    @property
    def is_ready(self) -> bool:
        return self._models_loaded

    def reload_models(self):
        self._load_models()

    def predict_battery_depletion(
        self,
        soc_history: List[float],
        voltage_history: List[float],
        temp_history: List[float],
    ) -> Dict[str, Any]:
        """Predict minutes until battery depletion using RF."""
        if self._battery_model is None:
            return {"available": False, "message": "Model not trained"}

        # Feature engineering from history: [curr_soc, curr_volt, curr_temp, discharge_rate]
        # Estimate discharge rate from history
        if len(soc_history) > 1:
             rate = (soc_history[0] - soc_history[-1]) / len(soc_history)
        else:
             rate = 0.5 # default

        features = [[
            soc_history[-1],      # Current SoC
            voltage_history[-1],  # Current Voltage
            temp_history[-1],     # Current Temp
            max(rate, 0.01),      # Discharge Rate Est
        ]]
        
        minutes_remaining = float(self._battery_model.predict(features)[0])
        
        # Risk assessment
        if minutes_remaining < 15: risk = "critical"
        elif minutes_remaining < 45: risk = "warning"
        else: risk = "normal"

        return {
            "available": True,
            "predicted_minutes_remaining": round(minutes_remaining, 1),
            "risk_level": risk,
            "model": "RandomForestRegressor"
        }

    def predict_tire_wear(
        self,
        fl_pressure: float,
        fr_pressure: float,
        rl_pressure: float,
        rr_pressure: float,
        odometer: float,
        avg_speed: float,
    ) -> Dict[str, Any]:
        """Predict tire wear score [0-1]."""
        if self._tire_model is None:
            return {"available": False, "message": "Model not trained"}

        features = [[
            fl_pressure, fr_pressure, rl_pressure, rr_pressure,
            odometer, avg_speed
        ]]
        
        wear_score = float(self._tire_model.predict(features)[0])
        wear_score = max(0.0, min(1.0, wear_score)) # clamp
        
        if wear_score > 0.7: risk = "critical"
        elif wear_score > 0.4: risk = "warning"
        else: risk = "normal"

        return {
            "available": True,
            "wear_score": round(wear_score, 4),
            "replacement_needed": wear_score > 0.7,
            "risk_level": risk,
            "model": "RandomForestRegressor"
        }

    def detect_anomalies(self, **kwargs) -> Dict[str, Any]:
        """
        Detect anomalies using IsolationForest.
        Inputs: speed, soc, voltage, temperature, fl, fr, rl, rr, throttle, brake, ev_range
        """
        if self._anomaly_model is None:
            return {"available": False, "message": "Model not trained"}

        features = [[
            kwargs.get('speed', 0),
            kwargs.get('soc', 0),
            kwargs.get('voltage', 0),
            kwargs.get('temperature', 0),
            kwargs.get('fl', 0), kwargs.get('fr', 0), kwargs.get('rl', 0), kwargs.get('rr', 0),
            kwargs.get('throttle', 0), kwargs.get('brake', 0), kwargs.get('ev_range', 0),
        ]]
        
        # IsolationForest: -1 is anomaly, 1 is normal
        pred = self._anomaly_model.predict(features)[0]
        score = self._anomaly_model.decision_function(features)[0]
        
        is_anomaly = (pred == -1)
        
        return {
            "available": True,
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": round(float(score), 4),
            "model": "IsolationForest"
        }

    def predict_all(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all predictions."""
        results = {"ml_models_available": self._models_loaded}
        
        soc = vehicle_data.get("battery_soc", 80)
        voltage = vehicle_data.get("battery_voltage", 380)
        temp = vehicle_data.get("battery_temp", 25)
        
        results["battery_prediction"] = self.predict_battery_depletion(
            soc_history=[soc]*10, voltage_history=[voltage]*10, temp_history=[temp]*10
        )
        
        tires = vehicle_data.get("tire_pressure", {})
        results["tire_prediction"] = self.predict_tire_wear(
            fl_pressure=tires.get("front_left", 32),
            fr_pressure=tires.get("front_right", 32),
            rl_pressure=tires.get("rear_left", 32),
            rr_pressure=tires.get("rear_right", 32),
            odometer=50000, # Mock odometer if missing
            avg_speed=60
        )
        
        results["anomaly_detection"] = self.detect_anomalies(
            speed=vehicle_data.get("speed", 0),
            soc=soc, voltage=voltage, temperature=temp,
            fl=tires.get("front_left", 32), fr=tires.get("front_right", 32),
            rl=tires.get("rear_left", 32), rr=tires.get("rear_right", 32),
            throttle=vehicle_data.get("throttle_position", 0),
            brake=vehicle_data.get("brake_position", 0),
            ev_range=vehicle_data.get("ev_range", 100),
        )
        
        return results


_predictor: Optional[VehicleMLPredictor] = None

def get_predictor() -> VehicleMLPredictor:
    global _predictor
    if _predictor is None:
        _predictor = VehicleMLPredictor()
    return _predictor
