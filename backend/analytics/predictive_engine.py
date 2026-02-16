"""
Predictive Analytics Engine.

Provides trend-based predictions and ML-lite analytics:
- Battery SoC decline rate prediction (linear regression)
- Tire wear estimation from pressure trends
- Driving efficiency scoring
- EV range prediction

Uses numpy for lightweight calculations — no heavy ML frameworks required.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """A single prediction result."""
    signal: str
    prediction_type: str
    current_value: float
    predicted_value: float
    confidence: float  # 0.0 - 1.0
    time_horizon_seconds: int
    message: str
    severity: str  # "info", "warning", "critical"


@dataclass
class DrivingScore:
    """Driving efficiency/behavior score."""
    overall_score: float  # 0-100
    speed_score: float
    braking_score: float
    efficiency_score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictiveReport:
    """Full predictive analytics report."""
    predictions: List[Prediction]
    driving_score: Optional[DrivingScore]
    data_points_analyzed: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def _linear_regression(values: List[float]) -> tuple[float, float]:
    """
    Simple linear regression: y = slope * x + intercept.
    Returns (slope, intercept).
    """
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, y_mean

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _r_squared(values: List[float], slope: float, intercept: float) -> float:
    """Calculate R² goodness of fit."""
    n = len(values)
    if n < 2:
        return 0.0

    y_mean = sum(values) / n
    ss_tot = sum((y - y_mean) ** 2 for y in values)
    ss_res = sum((y - (slope * i + intercept)) ** 2 for i, y in enumerate(values))

    if ss_tot == 0:
        return 1.0
    return max(0.0, 1.0 - ss_res / ss_tot)


def predict_battery_depletion(battery_history: List[Dict[str, Any]]) -> Optional[Prediction]:
    """
    Predict when battery will reach critical level based on SoC trend.
    """
    if len(battery_history) < 10:
        return None

    soc_values = [h["soc"] for h in battery_history]
    slope, intercept = _linear_regression(soc_values)

    if slope >= 0:
        return Prediction(
            signal="battery_soc",
            prediction_type="battery_depletion",
            current_value=soc_values[-1],
            predicted_value=soc_values[-1],
            confidence=0.5,
            time_horizon_seconds=0,
            message="Battery SoC is stable or increasing",
            severity="info",
        )

    # How many seconds until SoC = 10% (critical)?
    current = soc_values[-1]
    target = 10.0
    seconds_to_critical = int((target - current) / slope) if slope != 0 else 99999
    predicted_soc_60s = max(0, current + slope * 60)

    r2 = _r_squared(soc_values, slope, intercept)
    confidence = min(0.95, r2)

    severity = "info"
    if seconds_to_critical < 300:  # < 5 minutes
        severity = "critical"
    elif seconds_to_critical < 900:  # < 15 minutes
        severity = "warning"

    return Prediction(
        signal="battery_soc",
        prediction_type="battery_depletion",
        current_value=round(current, 1),
        predicted_value=round(predicted_soc_60s, 1),
        confidence=round(confidence, 2),
        time_horizon_seconds=seconds_to_critical,
        message=f"Battery SoC declining at {abs(slope):.2f}%/sec. "
                f"Predicted to reach 10% in {seconds_to_critical}s. "
                f"SoC in 60s: {predicted_soc_60s:.1f}%",
        severity=severity,
    )


def predict_tire_wear(tire_history: List[Dict[str, Any]], tire_id: str = "front_left") -> Optional[Prediction]:
    """
    Predict tire pressure trend based on recent history.
    """
    if len(tire_history) < 10:
        return None

    values = [h.get(tire_id, h.get("front_left", 32.0)) for h in tire_history]
    slope, intercept = _linear_regression(values)
    current = values[-1]
    predicted_60s = current + slope * 60
    r2 = _r_squared(values, slope, intercept)

    severity = "info"
    if predicted_60s < 25:
        severity = "critical"
    elif predicted_60s < 28:
        severity = "warning"

    return Prediction(
        signal=f"tire_pressure_{tire_id}",
        prediction_type="tire_wear",
        current_value=round(current, 1),
        predicted_value=round(predicted_60s, 1),
        confidence=round(min(0.95, r2), 2),
        time_horizon_seconds=60,
        message=f"{tire_id} tire pressure trend: {slope:.3f} PSI/sec. "
                f"Predicted in 60s: {predicted_60s:.1f} PSI",
        severity=severity,
    )


def calculate_driving_score(
    speed_history: List[Dict[str, Any]],
    battery_history: List[Dict[str, Any]],
) -> Optional[DrivingScore]:
    """
    Calculate a driving efficiency score based on telemetry history.
    """
    if len(speed_history) < 10:
        return None

    speeds = [h["speed"] for h in speed_history]
    avg_speed = sum(speeds) / len(speeds)
    max_speed = max(speeds)

    # Speed score: penalize excessive speed (>120 km/h)
    speed_score = max(0, 100 - max(0, (max_speed - 120)) * 2)

    # Quick speed changes indicate harsh braking/accel
    deltas = [abs(speeds[i] - speeds[i - 1]) for i in range(1, len(speeds))]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    braking_score = max(0, 100 - avg_delta * 10)

    # Efficiency: based on battery consumption rate
    if len(battery_history) >= 2:
        soc_start = battery_history[0]["soc"]
        soc_end = battery_history[-1]["soc"]
        soc_used = soc_start - soc_end
        km_driven = avg_speed * len(speed_history) / 3600
        if km_driven > 0 and soc_used > 0:
            kwh_per_km = (soc_used * 0.775)  # ~77.5 kWh battery assumed
            efficiency_score = max(0, 100 - kwh_per_km * 5)
        else:
            efficiency_score = 80.0
    else:
        efficiency_score = 80.0

    overall = (speed_score * 0.3 + braking_score * 0.4 + efficiency_score * 0.3)

    return DrivingScore(
        overall_score=round(overall, 1),
        speed_score=round(speed_score, 1),
        braking_score=round(braking_score, 1),
        efficiency_score=round(efficiency_score, 1),
        details={
            "avg_speed_kmh": round(avg_speed, 1),
            "max_speed_kmh": round(max_speed, 1),
            "avg_speed_change": round(avg_delta, 2),
            "data_points": len(speed_history),
        },
    )


def generate_predictive_report(store) -> PredictiveReport:
    """
    Generate a full predictive analytics report from the data store.
    """
    predictions: List[Prediction] = []

    # Battery depletion prediction
    batt_pred = predict_battery_depletion(store.battery_history)
    if batt_pred:
        predictions.append(batt_pred)

    # Tire wear predictions
    if hasattr(store, 'tire_history') and store.tire_history:
        for tire in ["front_left", "front_right", "rear_left", "rear_right"]:
            tire_pred = predict_tire_wear(store.tire_history, tire)
            if tire_pred:
                predictions.append(tire_pred)

    # Driving score
    driving = calculate_driving_score(
        store.speed_history,
        store.battery_history,
    )

    total_points = len(store.speed_history) + len(store.battery_history)

    return PredictiveReport(
        predictions=predictions,
        driving_score=driving,
        data_points_analyzed=total_points,
    )
