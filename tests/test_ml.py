"""
Tests for ML Training & Prediction Pipeline.
Validates data generation, model training, and inference.
"""

import pytest
import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTrainingDataGeneration:
    """Tests for synthetic training data generation."""

    def test_generate_training_data_returns_required_keys(self):
        from backend.ml.ml_trainer import generate_training_data
        data = generate_training_data(num_sequences=50, sequence_length=10, seed=42)
        required_keys = ["battery_X", "battery_y", "tire_X", "tire_y", "anomaly_X"]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"

    def test_battery_data_shape(self):
        from backend.ml.ml_trainer import generate_training_data
        data = generate_training_data(num_sequences=50, sequence_length=10, seed=42)
        assert data["battery_X"].shape[0] == data["battery_y"].shape[0]
        assert data["battery_X"].shape[1] == 4  # soc, voltage, temp, discharge_rate

    def test_tire_data_shape(self):
        from backend.ml.ml_trainer import generate_training_data
        data = generate_training_data(num_sequences=50, sequence_length=10, seed=42)
        assert data["tire_X"].shape[0] == data["tire_y"].shape[0]
        assert data["tire_X"].shape[1] == 6  # fl, fr, rl, rr, odometer, avg_speed

    def test_anomaly_data_shape(self):
        from backend.ml.ml_trainer import generate_training_data
        data = generate_training_data(num_sequences=50, sequence_length=10, seed=42)
        assert data["anomaly_X"].shape[1] == 11  # 11 telemetry features

    def test_deterministic_with_seed(self):
        from backend.ml.ml_trainer import generate_training_data
        d1 = generate_training_data(num_sequences=20, seed=123)
        d2 = generate_training_data(num_sequences=20, seed=123)
        assert (d1["battery_X"] == d2["battery_X"]).all()


class TestMLTrainer:
    """Tests for VehicleMLTrainer."""

    def test_trainer_initialization(self):
        from backend.ml.ml_trainer import VehicleMLTrainer
        trainer = VehicleMLTrainer()
        status = trainer.training_status
        assert status["status"] == "idle"
        assert status["progress"] == 0

    def test_train_all_models(self):
        from backend.ml.ml_trainer import VehicleMLTrainer, MODELS_DIR
        trainer = VehicleMLTrainer()
        result = trainer.train_all_models(num_sequences=50)

        # train_all_models returns a dict keyed by model name
        assert "battery_predictor" in result
        assert "tire_wear_detector" in result
        assert "anomaly_detector" in result

        # Check model files were saved
        for model_name in ["battery_predictor.joblib", "tire_wear_detector.joblib", "anomaly_detector.joblib"]:
            assert os.path.exists(os.path.join(MODELS_DIR, model_name))

        # Check final status
        assert trainer.training_status["status"] == "completed"


class TestMLPredictor:
    """Tests for VehicleMLPredictor."""

    @pytest.fixture(autouse=True)
    def ensure_models_trained(self):
        """Train models before prediction tests."""
        from backend.ml.ml_trainer import VehicleMLTrainer, MODELS_DIR
        if not os.path.exists(os.path.join(MODELS_DIR, "battery_predictor.joblib")):
            trainer = VehicleMLTrainer()
            trainer.train_all_models(num_sequences=50)

    def test_predictor_loads_models(self):
        from backend.ml.ml_predictor import VehicleMLPredictor
        predictor = VehicleMLPredictor()
        assert predictor.is_ready is True

    def test_battery_prediction(self):
        from backend.ml.ml_predictor import VehicleMLPredictor
        predictor = VehicleMLPredictor()
        result = predictor.predict_battery_depletion(
            soc_history=[80, 78, 76, 74, 72],
            voltage_history=[390, 388, 386, 384, 382],
            temp_history=[28, 28, 29, 29, 30],
        )
        assert result["available"] is True
        assert "predicted_minutes_remaining" in result
        assert result["predicted_minutes_remaining"] > 0

    def test_tire_wear_prediction(self):
        from backend.ml.ml_predictor import VehicleMLPredictor
        predictor = VehicleMLPredictor()
        result = predictor.predict_tire_wear(
            fl_pressure=32.0, fr_pressure=31.5,
            rl_pressure=31.8, rr_pressure=32.2,
            odometer=50000, avg_speed=60,
        )
        assert result["available"] is True
        assert 0 <= result["wear_score"] <= 1

    def test_anomaly_detection(self):
        from backend.ml.ml_predictor import VehicleMLPredictor
        predictor = VehicleMLPredictor()
        result = predictor.detect_anomalies(
            speed=60, soc=80, voltage=390, temperature=28,
            fl=32, fr=31.5, rl=31.8, rr=32.2,
            throttle=30, brake=0, ev_range=200,
        )
        assert result["available"] is True
        assert "is_anomaly" in result
        assert "anomaly_score" in result

    def test_predict_all(self):
        from backend.ml.ml_predictor import VehicleMLPredictor
        predictor = VehicleMLPredictor()
        result = predictor.predict_all({
            "speed": 60, "battery_soc": 80,
            "battery_voltage": 390, "battery_temp": 28,
            "tire_pressure": {"front_left": 32, "front_right": 31.5,
                              "rear_left": 31.8, "rear_right": 32.2},
            "throttle_position": 30, "brake_position": 0, "ev_range": 200,
        })
        assert result["ml_models_available"] is True
        assert "battery_prediction" in result
        assert "tire_prediction" in result
        assert "anomaly_detection" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
