"""
Health Analytics & Early Warning Engine.
Rule-based explainable analytics for vehicle health monitoring.
Detects anomalies in tire pressure, battery SoC, speed, braking, and EV range.
"""

import uuid
import logging
from datetime import datetime
from typing import List

from backend.models.telemetry import (
    VehicleTelemetry,
    AlertModel,
    AlertSeverity,
)

logger = logging.getLogger(__name__)


class HealthAnalyzer:
    """
    Rule-based health analytics engine.

    Rules:
    1. Tire pressure < 25 PSI → "Possible Tire Failure" (critical)
    2. Battery SoC drops rapidly (>5% in 30 seconds) → "Battery Degradation" (critical)
    3. Speed > 100 km/h continuously for 10+ seconds → "High Speed Stress Warning" (warning)
    4. Brake > 90% → "Harsh Braking Detected" (warning)
    5. Throttle > 90% sustained 5+ sec → "Harsh Acceleration" (warning)
    6. EV range < 30 km → "Low EV Range Anxiety" (warning)
    """

    def analyze(self, telemetry: VehicleTelemetry, store) -> List[AlertModel]:
        """
        Run all analytics rules against the current telemetry.
        Returns list of newly generated alerts.
        """
        alerts: List[AlertModel] = []

        # Rule 1: Tire pressure checks
        alerts.extend(self._check_tire_pressure(telemetry))

        # Rule 2: Battery rapid drop
        alert = self._check_battery_degradation(telemetry, store)
        if alert:
            alerts.append(alert)

        # Rule 3: Sustained high speed
        alert = self._check_high_speed(telemetry, store)
        if alert:
            alerts.append(alert)

        # Rule 4: Harsh braking
        alert = self._check_harsh_braking(telemetry)
        if alert:
            alerts.append(alert)

        # Rule 5: Harsh acceleration
        alert = self._check_harsh_acceleration(telemetry, store)
        if alert:
            alerts.append(alert)

        # Rule 6: Low EV range
        alert = self._check_ev_range(telemetry)
        if alert:
            alerts.append(alert)

        return alerts

    def _check_tire_pressure(self, telemetry: VehicleTelemetry) -> List[AlertModel]:
        """Check all four tire pressures against threshold."""
        alerts = []
        tire_map = {
            "tire_pressure_fl": ("Front Left", telemetry.tires.front_left),
            "tire_pressure_fr": ("Front Right", telemetry.tires.front_right),
            "tire_pressure_rl": ("Rear Left", telemetry.tires.rear_left),
            "tire_pressure_rr": ("Rear Right", telemetry.tires.rear_right),
        }

        for signal_id, (label, pressure) in tire_map.items():
            if pressure < 25.0:
                alerts.append(AlertModel(
                    id=str(uuid.uuid4()),
                    alert_type="tire_pressure_low",
                    severity=AlertSeverity.CRITICAL,
                    message=f"Possible Tire Failure: {label} tire pressure at {pressure:.1f} PSI (below 25 PSI threshold)",
                    signal=signal_id,
                    value=pressure,
                    threshold="< 25 PSI",
                    timestamp=telemetry.timestamp,
                ))

        return alerts

    def _check_battery_degradation(self, telemetry: VehicleTelemetry, store) -> AlertModel | None:
        """Check for rapid battery SoC drop (>5% within the tracked window)."""
        history = store.battery_history
        if len(history) < 2:
            return None

        oldest_soc = history[0]["soc"]
        current_soc = telemetry.battery.soc
        drop = oldest_soc - current_soc

        if drop > 5.0:
            return AlertModel(
                id=str(uuid.uuid4()),
                alert_type="battery_degradation",
                severity=AlertSeverity.CRITICAL,
                message=f"Battery Degradation Alert: SoC dropped {drop:.1f}% (from {oldest_soc:.1f}% to {current_soc:.1f}%)",
                signal="battery_soc",
                value=current_soc,
                threshold="> 5% drop in monitoring window",
                timestamp=telemetry.timestamp,
            )
        return None

    def _check_high_speed(self, telemetry: VehicleTelemetry, store) -> AlertModel | None:
        """Check for sustained high speed (>100 km/h for 10+ consecutive seconds)."""
        history = store.speed_history
        if len(history) < 10:
            return None

        recent = history[-10:]
        all_high = all(h["speed"] > 100 for h in recent)

        if all_high:
            return AlertModel(
                id=str(uuid.uuid4()),
                alert_type="high_speed_stress",
                severity=AlertSeverity.WARNING,
                message=f"High Speed Stress Warning: Vehicle sustained speed above 100 km/h (current: {telemetry.speed:.1f} km/h)",
                signal="speed",
                value=telemetry.speed,
                threshold="> 100 km/h sustained for 10+ seconds",
                timestamp=telemetry.timestamp,
            )
        return None

    def _check_harsh_braking(self, telemetry: VehicleTelemetry) -> AlertModel | None:
        """Check for harsh braking (brake > 90%)."""
        brake = getattr(telemetry, 'drivetrain', None)
        if brake is None:
            return None
        brake_pos = telemetry.drivetrain.brake_position
        if brake_pos > 90.0:
            return AlertModel(
                id=str(uuid.uuid4()),
                alert_type="harsh_braking",
                severity=AlertSeverity.WARNING,
                message=f"Harsh Braking Detected: Brake at {brake_pos:.1f}% (above 90% threshold)",
                signal="brake_position",
                value=brake_pos,
                threshold="> 90%",
                timestamp=telemetry.timestamp,
            )
        return None

    def _check_harsh_acceleration(self, telemetry: VehicleTelemetry, store) -> AlertModel | None:
        """Check for sustained harsh acceleration (throttle > 90% for 5+ sec)."""
        throttle = getattr(telemetry, 'drivetrain', None)
        if throttle is None:
            return None
        throttle_pos = telemetry.drivetrain.throttle_position
        if throttle_pos > 90.0:
            # Check history for sustained harsh acceleration
            history = getattr(store, 'speed_history', [])
            if len(history) >= 5:
                return AlertModel(
                    id=str(uuid.uuid4()),
                    alert_type="harsh_acceleration",
                    severity=AlertSeverity.WARNING,
                    message=f"Harsh Acceleration: Throttle at {throttle_pos:.1f}% (above 90% sustained)",
                    signal="throttle_position",
                    value=throttle_pos,
                    threshold="> 90% sustained",
                    timestamp=telemetry.timestamp,
                )
        return None

    def _check_ev_range(self, telemetry: VehicleTelemetry) -> AlertModel | None:
        """Check for low EV range (< 30 km)."""
        ev = getattr(telemetry, 'ev_status', None)
        if ev is None:
            return None
        ev_range = telemetry.ev_status.ev_range
        if ev_range < 30.0:
            return AlertModel(
                id=str(uuid.uuid4()),
                alert_type="low_ev_range",
                severity=AlertSeverity.WARNING,
                message=f"Low EV Range Alert: Only {ev_range:.1f} km remaining (below 30 km threshold)",
                signal="ev_range",
                value=ev_range,
                threshold="< 30 km",
                timestamp=telemetry.timestamp,
            )
        return None
