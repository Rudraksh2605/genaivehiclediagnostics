"""
ML Model Trainer for Vehicle Diagnostics (Scikit-Learn Version).

Trains efficient ML models on simulated vehicle telemetry data:
  - Battery Predictor: RandomForestRegressor (predicts time until <20% SoC)
  - Tire Wear Detector: RandomForestRegressor (predicts wear score)
  - Anomaly Detector: IsolationForest (detects unusual sensor patterns)

Replaced TensorFlow due to installation issues on Windows environment.
"""

import logging
import os
import time
import json
import joblib
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

logger = logging.getLogger(__name__)

# ── Save Directory ───────────────────────────────────────────────────────────

MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
os.makedirs(MODELS_DIR, exist_ok=True)


# ── Training Data Generator ─────────────────────────────────────────────────

def generate_training_data(
    num_sequences: int = 2000,
    sequence_length: int = 50,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Load real-world vehicle telemetry data for training from Kaggle-style CSV.
    Falls back to synthetic generation if the file is missing.
    """
    np.random.seed(seed)
    
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "telemetry_dataset.csv")
    
    if os.path.exists(csv_path):
        logger.info(f"Loading real-world training data from {csv_path}...")
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            
            # Limit to num_sequences
            df = df.sample(n=min(num_sequences, len(df)), random_state=seed)
            
            # ── Battery SoC Prediction Data (Flattened for RF) ───────────────────
            # Features: [soc, voltage, temp, discharge_rate]
            # Label: minutes until SoC < 20%
            battery_X = df[['battery_soc', 'battery_voltage', 'battery_temp', 'discharge_rate']].values
            battery_y = df['minutes_to_20_soc'].values
            
            # ── Tire Wear Prediction Data ────────────────────────────────────────
            # Features: [FL_psi, FR_psi, RL_psi, RR_psi, odometer, speed]
            # Label: wear score [0=new, 1=needs replacement]
            tire_X = df[['tire_fl_psi', 'tire_fr_psi', 'tire_rl_psi', 'tire_rr_psi', 'odometer', 'speed']].values
            tire_y = df['tire_wear_label'].values
            
            # ── Anomaly Detection Data ───────────────────────────────────────────
            # Features: 11 signals
            anomaly_X = df[['speed', 'battery_soc', 'battery_voltage', 'battery_temp', 
                           'tire_fl_psi', 'tire_fr_psi', 'tire_rl_psi', 'tire_rr_psi', 
                           'throttle', 'brake', 'ev_range']].values
                           
            return {
                "battery_X": battery_X,
                "battery_y": battery_y,
                "tire_X": tire_X,
                "tire_y": tire_y,
                "anomaly_X": anomaly_X,
            }
        except Exception as e:
            logger.error(f"Failed to load CSV dataset: {e}. Falling back to synthetic.")
            
    logger.info(f"Generating {num_sequences} synthetic training samples (fallback)...")

    # ── Fallback Synthetic Generation (if CSV missing) ───────────────────────
    battery_X = []
    battery_y = []
    for _ in range(num_sequences):
        current_soc = np.random.uniform(25, 100)
        discharge_rate = np.random.uniform(0.1, 1.5)
        battery_X.append([current_soc, 320 + (current_soc / 100) * 80 + np.random.normal(0, 1), np.random.uniform(15, 40), discharge_rate + np.random.normal(0, 0.05)])
        battery_y.append((current_soc - 20) / max(discharge_rate, 0.01) if current_soc > 20 else 0)

    tire_X = []
    tire_y = []
    for _ in range(num_sequences):
        wear_level = np.random.uniform(0, 1)
        base_pressure = 35.0 - wear_level * 12.0
        tire_X.append([base_pressure + np.random.normal(0, 1.5), base_pressure + np.random.normal(0, 1.5), base_pressure + np.random.normal(0, 2.0), base_pressure + np.random.normal(0, 2.0), np.random.uniform(0, 100000) * (0.3 + wear_level * 0.7), np.random.uniform(30, 120)])
        tire_y.append(wear_level)

    anomaly_normal = []
    for _ in range(num_sequences):
        soc = np.random.uniform(20, 100)
        anomaly_normal.append([np.random.uniform(0, 180), soc, 320 + (soc / 100) * 80, np.random.uniform(15, 40), np.random.uniform(28, 36), np.random.uniform(28, 36), np.random.uniform(28, 36), np.random.uniform(28, 36), np.random.uniform(0, 100), np.random.uniform(0, 100), soc * 3.5])

    return {
        "battery_X": np.array(battery_X),
        "battery_y": np.array(battery_y),
        "tire_X": np.array(tire_X),
        "tire_y": np.array(tire_y),
        "anomaly_X": np.array(anomaly_normal),
    }


# ── Model Training ──────────────────────────────────────────────────────────

class VehicleMLTrainer:
    """Trains Scikit-Learn models for vehicle diagnostics."""

    def __init__(self):
        self._training_status: Dict[str, Any] = {
            "status": "idle",
            "progress": 0,
            "current_model": None,
            "results": {},
            "backend": "scikit-learn (CPU)",
        }

    @property
    def training_status(self) -> Dict[str, Any]:
        return self._training_status.copy()

    def train_all_models(
        self,
        num_sequences: int = 2000,
        epochs: int = 50,  # Unused in sklearn, kept for API compat
        batch_size: int = 32, # Unused
    ) -> Dict[str, Any]:
        
        self._training_status["status"] = "generating_data"
        self._training_status["progress"] = 5
        
        data = generate_training_data(num_sequences)
        results = {}
        total_start = time.perf_counter()

        # 1. Battery Predictor (RandomForest)
        self._training_status["current_model"] = "battery_predictor"
        self._training_status["status"] = "training"
        self._training_status["progress"] = 15
        logger.info("Training Battery Predictor (RF)...")

        model_bat = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        X_train, X_val, y_train, y_val = train_test_split(data["battery_X"], data["battery_y"], test_size=0.2)
        
        start = time.perf_counter()
        model_bat.fit(X_train, y_train)
        training_time = time.perf_counter() - start
        
        val_mae = mean_absolute_error(y_val, model_bat.predict(X_val))
        path_bat = os.path.join(MODELS_DIR, "battery_predictor.joblib")
        joblib.dump(model_bat, path_bat)
        
        results["battery_predictor"] = {
            "model": "RandomForestRegressor",
            "val_mae_minutes": round(val_mae, 2),
            "training_time_s": round(training_time, 2),
            "model_path": path_bat
        }
        self._training_status["progress"] = 45
        self._training_status["results"]["battery_predictor"] = results["battery_predictor"]

        # 2. Tire Wear Detector (RandomForest)
        self._training_status["current_model"] = "tire_wear_detector"
        self._training_status["progress"] = 50
        logger.info("Training Tire Wear Detector (RF)...")
        
        model_tire = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        X_train, X_val, y_train, y_val = train_test_split(data["tire_X"], data["tire_y"], test_size=0.2)
        
        start = time.perf_counter()
        model_tire.fit(X_train, y_train)
        training_time = time.perf_counter() - start
        
        val_mae = mean_absolute_error(y_val, model_tire.predict(X_val))
        path_tire = os.path.join(MODELS_DIR, "tire_wear_detector.joblib")
        joblib.dump(model_tire, path_tire)
        
        results["tire_wear_detector"] = {
            "model": "RandomForestRegressor",
            "val_mae_score": round(val_mae, 4),
            "training_time_s": round(training_time, 2),
            "model_path": path_tire
        }
        self._training_status["progress"] = 75
        self._training_status["results"]["tire_wear_detector"] = results["tire_wear_detector"]

        # 3. Anomaly Detector (IsolationForest)
        self._training_status["current_model"] = "anomaly_detector"
        self._training_status["progress"] = 80
        logger.info("Training Anomaly Detector (IsolationForest)...")
        
        model_anom = IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=-1)
        
        start = time.perf_counter()
        model_anom.fit(data["anomaly_X"])
        training_time = time.perf_counter() - start
        
        path_anom = os.path.join(MODELS_DIR, "anomaly_detector.joblib")
        joblib.dump(model_anom, path_anom)
        
        results["anomaly_detector"] = {
            "model": "IsolationForest",
            "training_time_s": round(training_time, 2),
            "model_path": path_anom
        }
        self._training_status["progress"] = 95
        self._training_status["results"]["anomaly_detector"] = results["anomaly_detector"]

        total_time = time.perf_counter() - total_start
        self._training_status["status"] = "completed"
        self._training_status["progress"] = 100
        self._training_status["current_model"] = None
        self._training_status["total_training_time_s"] = round(total_time, 2)
        
        return results


_trainer: Optional[VehicleMLTrainer] = None

def get_trainer() -> VehicleMLTrainer:
    global _trainer
    if _trainer is None:
        _trainer = VehicleMLTrainer()
    return _trainer
