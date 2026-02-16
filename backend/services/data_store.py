"""
In-memory data store for vehicle telemetry, alerts, and simulation state.
Provides thread-safe singleton storage with mock data fallback.
"""

import json
import os
import logging
from typing import List, Optional
from datetime import datetime

from backend.models.telemetry import (
    VehicleTelemetry,
    BatteryHealth,
    TireStatus,
    AlertModel,
    SimulationStatus,
    SignalConfig,
)

logger = logging.getLogger(__name__)


class DataStore:
    """
    Singleton in-memory data store for the vehicle diagnostics system.
    Stores latest telemetry, alert history, and simulation status.
    Falls back to mock data when the simulator is not running.
    """

    _instance: Optional["DataStore"] = None

    def __new__(cls) -> "DataStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # Latest telemetry snapshot
        self.telemetry: VehicleTelemetry = self._get_mock_telemetry()

        # Alert history
        self.alerts: List[AlertModel] = []

        # Simulation state
        self.simulation: SimulationStatus = SimulationStatus()

        # Historical battery SoC values for rapid-drop detection
        self.battery_history: List[dict] = []

        # Historical speed values for sustained-speed detection
        self.speed_history: List[dict] = []

        # Historical tire pressure for wear detection
        self.tire_history: List[dict] = []

        # Loaded signal configuration
        self.signal_configs: List[SignalConfig] = []

        # Load signal config from file
        self._load_signal_config()

        logger.info("DataStore initialized with mock fallback data")

    def _get_mock_telemetry(self) -> VehicleTelemetry:
        """Return mock telemetry data (used when simulator is off)."""
        return VehicleTelemetry(
            timestamp=datetime.utcnow().isoformat(),
            speed=60.0,
            battery=BatteryHealth(
                soc=85.0,
                voltage=395.0,
                temperature=28.0,
                health_status="Good",
            ),
            tires=TireStatus(
                front_left=32.0,
                front_right=31.5,
                rear_left=31.8,
                rear_right=32.2,
            ),
            odometer=15234.5,
            engine_status="running",
        )

    def _load_signal_config(self) -> None:
        """Load signal configuration from config/signals_config.json."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "config",
            "signals_config.json",
        )
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            self.signal_configs = [
                SignalConfig(**sig) for sig in config_data.get("signals", [])
            ]
            logger.info(f"Loaded {len(self.signal_configs)} signal configs from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Signal config not found at {config_path}, using defaults")
        except Exception as e:
            logger.error(f"Error loading signal config: {e}")

    def update_telemetry(self, telemetry: VehicleTelemetry) -> None:
        """Update the latest telemetry snapshot and track history."""
        self.telemetry = telemetry

        # Track battery history for rapid-drop detection
        self.battery_history.append({
            "timestamp": datetime.utcnow().timestamp(),
            "soc": telemetry.battery.soc,
        })
        # Keep only last 60 seconds of history
        cutoff = datetime.utcnow().timestamp() - 60
        self.battery_history = [
            h for h in self.battery_history if h["timestamp"] > cutoff
        ]

        # Track speed history for sustained-speed detection
        self.speed_history.append({
            "timestamp": datetime.utcnow().timestamp(),
            "speed": telemetry.speed,
        })
        # Keep only last 30 seconds of history
        speed_cutoff = datetime.utcnow().timestamp() - 30
        self.speed_history = [
            h for h in self.speed_history if h["timestamp"] > speed_cutoff
        ]

        # Track tire history for wear prediction
        self.tire_history.append({
            "timestamp": datetime.utcnow().timestamp(),
            "front_left": telemetry.tires.front_left,
            "front_right": telemetry.tires.front_right,
            "rear_left": telemetry.tires.rear_left,
            "rear_right": telemetry.tires.rear_right,
        })
        tire_cutoff = datetime.utcnow().timestamp() - 60
        self.tire_history = [
            h for h in self.tire_history if h["timestamp"] > tire_cutoff
        ]

    def add_alert(self, alert: AlertModel) -> None:
        """Add an alert to the history, avoiding near-duplicate alerts."""
        # Prevent duplicate alerts within 10 seconds
        for existing in self.alerts[-20:]:
            if (
                existing.alert_type == alert.alert_type
                and existing.signal == alert.signal
                and abs(
                    datetime.fromisoformat(existing.timestamp).timestamp()
                    - datetime.fromisoformat(alert.timestamp).timestamp()
                ) < 10
            ):
                return
        self.alerts.append(alert)
        # Keep only the latest 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        logger.info(f"Alert added: [{alert.severity.value}] {alert.message}")

    def get_alerts(self, limit: int = 50) -> List[AlertModel]:
        """Return the most recent alerts."""
        return list(reversed(self.alerts[-limit:]))

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self.alerts.clear()

    def reset(self) -> None:
        """Reset the data store to initial state."""
        self.telemetry = self._get_mock_telemetry()
        self.alerts.clear()
        self.battery_history.clear()
        self.speed_history.clear()
        self.tire_history.clear()
        self.simulation = SimulationStatus()
        logger.info("DataStore reset to initial state")
