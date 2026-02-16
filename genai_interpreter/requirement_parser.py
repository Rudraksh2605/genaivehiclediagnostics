"""
GenAI Requirement Interpreter.
Parses natural-language vehicle diagnostics requirements and extracts
signals, services, UI components, and alert types into a structured blueprint.

Uses rule-based NLP (keyword matching + regex). Includes an LLM integration
stub for future expansion.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# ── Signal keyword mappings ──────────────────────────────────────────────────
SIGNAL_KEYWORDS: Dict[str, List[str]] = {
    "speed": ["speed", "velocity", "speedometer", "mph", "km/h", "kph"],
    "battery_soc": [
        "battery", "soc", "state of charge", "battery health",
        "charging", "charge level", "battery level", "ev battery",
    ],
    "tire_pressure": [
        "tire", "tyre", "tire pressure", "tyre pressure", "tpms",
        "inflation", "psi",
    ],
    "throttle_position": [
        "throttle", "accelerator", "gas pedal", "throttle position",
    ],
    "brake_position": [
        "brake", "braking", "brake pedal", "brake position", "abs",
    ],
    "gear_position": [
        "gear", "transmission", "gearbox", "shift", "gear position",
    ],
    "steering_angle": [
        "steering", "steering wheel", "steering angle", "steer",
    ],
    "ev_range": [
        "range", "ev range", "remaining range", "distance remaining",
        "estimated range",
    ],
    "engine_temp": [
        "engine temperature", "engine temp", "coolant", "overheating",
        "thermal",
    ],
    "fuel_level": [
        "fuel", "fuel level", "gas", "petrol", "diesel",
    ],
    "odometer": ["odometer", "mileage", "distance", "trip"],
    "acceleration": [
        "acceleration", "g-force", "deceleration",
    ],
    "gps_location": [
        "gps", "location", "position", "coordinates", "geolocation",
    ],
}

# ── Service mappings ─────────────────────────────────────────────────────────
SERVICE_KEYWORDS: Dict[str, List[str]] = {
    "health_monitoring": [
        "monitor", "monitoring", "health", "diagnostics", "diagnostic",
        "status", "check", "track", "tracking", "observe",
    ],
    "alert_service": [
        "alert", "warning", "alarm", "notification", "notify",
        "abnormal", "anomaly", "anomalies", "failure", "critical",
    ],
    "predictive_maintenance": [
        "predict", "predictive", "maintenance", "forecast", "prognosis",
    ],
    "data_logging": [
        "log", "logging", "record", "history", "historical", "store",
    ],
    "remote_control": [
        "remote", "control", "command", "actuate",
    ],
}

# ── UI widget mappings ───────────────────────────────────────────────────────
SIGNAL_TO_WIDGET: Dict[str, str] = {
    "speed": "speed_gauge",
    "battery_soc": "battery_indicator",
    "tire_pressure": "tire_pressure_card",
    "throttle_position": "throttle_bar",
    "brake_position": "brake_bar",
    "gear_position": "gear_indicator",
    "steering_angle": "steering_wheel",
    "ev_range": "ev_range_display",
    "engine_temp": "engine_temp_gauge",
    "fuel_level": "fuel_level_bar",
    "odometer": "odometer_display",
    "acceleration": "acceleration_meter",
    "gps_location": "map_widget",
}

# ── Alert type mappings ──────────────────────────────────────────────────────
SIGNAL_TO_ALERTS: Dict[str, List[str]] = {
    "speed": ["high_speed_stress"],
    "battery_soc": ["battery_degradation", "low_battery"],
    "tire_pressure": ["tire_pressure_drop", "tire_failure"],
    "throttle_position": ["harsh_acceleration"],
    "brake_position": ["harsh_braking"],
    "ev_range": ["low_ev_range"],
    "engine_temp": ["engine_overheating"],
    "fuel_level": ["low_fuel"],
    "acceleration": ["harsh_braking", "harsh_acceleration"],
}


class RequirementParser:
    """
    Parses natural-language vehicle diagnostics requirements
    and outputs a structured JSON blueprint.
    """

    def parse(self, requirement: str) -> Dict[str, Any]:
        """
        Parse a requirement string and return a structured blueprint.

        Args:
            requirement: Natural-language description of vehicle diagnostics need.

        Returns:
            Dictionary with keys: signals, services, ui_components, alerts, raw_requirement
        """
        if not requirement or not requirement.strip():
            logger.warning("Empty requirement received")
            return self._empty_blueprint(requirement)

        logger.info(f"Parsing requirement: {requirement[:80]}...")

        requirement_lower = requirement.lower()

        # Extract components
        signals = self._extract_signals(requirement_lower)
        services = self._extract_services(requirement_lower)
        ui_components = self._derive_ui_components(signals)
        alerts = self._derive_alerts(signals)

        # If no specific signals found, use defaults
        if not signals:
            logger.info("No specific signals found — using default vehicle signals")
            signals = ["speed", "battery_soc", "tire_pressure"]
            ui_components = ["speed_gauge", "battery_indicator", "tire_pressure_card"]
            alerts = ["high_speed_stress", "battery_degradation", "tire_pressure_drop"]

        # Ensure at least health_monitoring service
        if not services:
            services = ["health_monitoring"]

        blueprint = {
            "signals": signals,
            "services": services,
            "ui_components": ui_components,
            "alerts": alerts,
            "raw_requirement": requirement,
        }

        logger.info(
            f"Blueprint generated: {len(signals)} signals, "
            f"{len(services)} services, {len(ui_components)} UI widgets, "
            f"{len(alerts)} alert types"
        )

        return blueprint

    def _extract_signals(self, text: str) -> List[str]:
        """Extract vehicle signals mentioned in the requirement text."""
        found = []
        for signal_id, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if signal_id not in found:
                        found.append(signal_id)
                    break
        return found

    def _extract_services(self, text: str) -> List[str]:
        """Extract required services from the requirement text."""
        found = []
        for service_id, keywords in SERVICE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if service_id not in found:
                        found.append(service_id)
                    break
        return found

    def _derive_ui_components(self, signals: List[str]) -> List[str]:
        """Map extracted signals to UI widget names."""
        widgets = []
        for signal in signals:
            widget = SIGNAL_TO_WIDGET.get(signal, f"{signal}_card")
            if widget not in widgets:
                widgets.append(widget)
        return widgets

    def _derive_alerts(self, signals: List[str]) -> List[str]:
        """Map extracted signals to potential alert types."""
        alerts = []
        for signal in signals:
            for alert in SIGNAL_TO_ALERTS.get(signal, []):
                if alert not in alerts:
                    alerts.append(alert)
        return alerts

    def _empty_blueprint(self, requirement: str) -> Dict[str, Any]:
        """Return an empty blueprint."""
        return {
            "signals": [],
            "services": [],
            "ui_components": [],
            "alerts": [],
            "raw_requirement": requirement or "",
        }

    def parse_with_llm_stub(self, requirement: str) -> Dict[str, Any]:
        """
        LLM integration stub for future expansion.
        Replace this with actual LLM API call (OpenAI, Google PaLM, etc.)
        when ready for production LLM-based parsing.

        Currently falls back to rule-based parsing.
        """
        logger.info("LLM stub called — falling back to rule-based parsing")
        # Future: Call LLM API here
        # prompt = f"Extract vehicle signals, services, UI components, and alerts from: {requirement}"
        # response = llm_client.generate(prompt)
        # return json.loads(response)
        return self.parse(requirement)

    def to_json(self, blueprint: Dict[str, Any], indent: int = 2) -> str:
        """Serialize a blueprint to formatted JSON string."""
        return json.dumps(blueprint, indent=indent)


# ── Module-level convenience functions ───────────────────────────────────────

def parse_requirement(requirement: str) -> Dict[str, Any]:
    """Parse a requirement and return the blueprint dictionary."""
    parser = RequirementParser()
    return parser.parse(requirement)


def parse_requirement_json(requirement: str) -> str:
    """Parse a requirement and return the blueprint as a JSON string."""
    parser = RequirementParser()
    blueprint = parser.parse(requirement)
    return parser.to_json(blueprint)


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_req = (
        "Monitor vehicle speed, battery SoC, and tire pressure "
        "and generate alerts on abnormal behavior."
    )
    print("=" * 60)
    print("GenAI Requirement Interpreter")
    print("=" * 60)
    print(f"\nInput Requirement:\n  \"{sample_req}\"\n")

    result = parse_requirement(sample_req)
    print("Generated Blueprint:")
    print(json.dumps(result, indent=2))
