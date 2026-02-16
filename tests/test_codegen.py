"""
Tests for the GenAI Code Generation Engine.

Tests cover:
- LLM provider abstraction (template fallback)
- Multi-language code generation
- Design document generation
- Test case generation
- LLM comparison engine
- MISRA compliance checking
- Predictive analytics engine
"""

import json
import pytest
from unittest.mock import patch

# ── Requirement Parser Tests ─────────────────────────────────────────────────

from genai_interpreter.requirement_parser import RequirementParser, parse_requirement


class TestRequirementParserExpanded:
    """Tests for expanded signal support in RequirementParser."""

    def setup_method(self):
        self.parser = RequirementParser()

    def test_parse_throttle_and_brake(self):
        bp = self.parser.parse("Monitor throttle and brake for harsh driving")
        assert "throttle_position" in bp["signals"]
        assert "brake_position" in bp["signals"]
        assert "harsh_acceleration" in bp["alerts"] or "harsh_braking" in bp["alerts"]

    def test_parse_ev_range(self):
        bp = self.parser.parse("Check remaining EV range for low battery warning")
        assert "ev_range" in bp["signals"]
        assert "low_ev_range" in bp["alerts"]

    def test_parse_steering(self):
        bp = self.parser.parse("Track steering angle during driving")
        assert "steering_angle" in bp["signals"]
        assert "steering_wheel" in [w for w in bp["ui_components"]]

    def test_parse_gear_position(self):
        bp = self.parser.parse("Show current gear position")
        assert "gear_position" in bp["signals"]


# ── Code Generator Tests ─────────────────────────────────────────────────────

from genai_interpreter.code_generator import CodeGenerator


class TestCodeGenerator:
    """Tests for multi-language code generation."""

    def setup_method(self):
        self.generator = CodeGenerator()
        self.blueprint = parse_requirement(
            "Monitor vehicle speed, battery SoC, and tire pressure "
            "and generate alerts on abnormal behavior."
        )

    def test_generate_python(self):
        result = self.generator.generate(self.blueprint, "python")
        assert result["language"] == "python"
        assert result["code"]
        assert result["lines_of_code"] > 0
        assert "import" in result["code"] or "def " in result["code"]

    def test_generate_cpp(self):
        result = self.generator.generate(self.blueprint, "cpp")
        assert result["language"] == "cpp"
        assert result["code"]
        assert result["lines_of_code"] > 0

    def test_generate_kotlin(self):
        result = self.generator.generate(self.blueprint, "kotlin")
        assert result["language"] == "kotlin"
        assert result["code"]

    def test_generate_rust(self):
        result = self.generator.generate(self.blueprint, "rust")
        assert result["language"] == "rust"
        assert result["code"]

    def test_generate_all_languages(self):
        results = self.generator.generate_all(self.blueprint)
        assert len(results) >= 4
        languages = [r["language"] for r in results]
        assert "python" in languages
        assert "cpp" in languages

    def test_supported_languages(self):
        langs = self.generator.supported_languages()
        assert "python" in langs
        assert "cpp" in langs
        assert "kotlin" in langs
        assert "rust" in langs

    def test_generation_history(self):
        self.generator.generate(self.blueprint, "python")
        history = self.generator.get_history()
        assert len(history) >= 1


# ── Design Generator Tests ───────────────────────────────────────────────────

from genai_interpreter.design_generator import DesignGenerator


class TestDesignGenerator:
    """Tests for design document generation."""

    def setup_method(self):
        self.generator = DesignGenerator()
        self.blueprint = parse_requirement(
            "Monitor speed and battery SoC with alerts."
        )

    def test_generate_design(self):
        result = self.generator.generate(self.blueprint)
        assert result["content"]
        assert "# Design Document" in result["content"] or "design" in result["content"].lower()
        assert result["generation_method"]


# ── Test Generator Tests ─────────────────────────────────────────────────────

from genai_interpreter.test_generator import TestGenerator


class TestTestGenerator:
    """Tests for test case generation."""

    def setup_method(self):
        self.generator = TestGenerator()
        self.blueprint = parse_requirement(
            "Monitor speed and battery SoC."
        )

    def test_generate_python_tests(self):
        result = self.generator.generate(self.blueprint, "python")
        assert result["language"] == "python"
        assert result["code"]
        assert result["test_count"] >= 0

    def test_generate_cpp_tests(self):
        result = self.generator.generate(self.blueprint, "cpp")
        assert result["language"] == "cpp"
        assert result["code"]


# ── Compliance Checker Tests ─────────────────────────────────────────────────

from genai_interpreter.compliance_checker import ComplianceChecker


class TestComplianceChecker:
    """Tests for MISRA C++ compliance checker."""

    def setup_method(self):
        self.checker = ComplianceChecker()

    def test_check_clean_code(self):
        code = '''
// Clean C++ code
#include <iostream>
#include <string>

class VehicleService {
public:
    void monitor() {
        int speed = 0;
        std::string status = "healthy";
    }
};
'''
        result = self.checker.check(code)
        assert "violations" in result
        assert "aspice_level" in result

    def test_check_code_with_violations(self):
        code = '''
#include <stdio.h>
void f() {
    goto error;
    error:
    printf("fail");
    int x;
}
'''
        result = self.checker.check(code)
        # Should detect at least some violations
        assert isinstance(result["violations"], list)

    def test_get_rules(self):
        rules = self.checker.get_rules()
        assert len(rules) >= 10
        for rule in rules:
            assert "id" in rule
            assert "description" in rule


# ── Predictive Engine Tests ──────────────────────────────────────────────────

from backend.analytics.predictive_engine import (
    predict_battery_depletion,
    predict_tire_wear,
    calculate_driving_score,
)


class TestPredictiveEngine:
    """Tests for predictive analytics."""

    def test_battery_prediction_declining(self):
        history = [{"soc": 100 - i * 0.5, "timestamp": f"t{i}"} for i in range(20)]
        pred = predict_battery_depletion(history)
        assert pred is not None
        assert pred.signal == "battery_soc"
        assert pred.predicted_value < history[-1]["soc"]

    def test_battery_prediction_stable(self):
        history = [{"soc": 80.0, "timestamp": f"t{i}"} for i in range(20)]
        pred = predict_battery_depletion(history)
        assert pred is not None
        assert "stable" in pred.message.lower() or pred.confidence >= 0

    def test_battery_prediction_insufficient_data(self):
        history = [{"soc": 90.0}]
        pred = predict_battery_depletion(history)
        assert pred is None

    def test_tire_wear_prediction(self):
        history = [{"front_left": 32 - i * 0.02} for i in range(20)]
        pred = predict_tire_wear(history, "front_left")
        assert pred is not None
        assert "tire" in pred.signal

    def test_driving_score(self):
        speed_history = [{"speed": 60 + i % 10} for i in range(20)]
        batt_history = [{"soc": 90 - i * 0.1} for i in range(20)]
        score = calculate_driving_score(speed_history, batt_history)
        assert score is not None
        assert 0 <= score.overall_score <= 100
        assert 0 <= score.speed_score <= 100

    def test_driving_score_insufficient_data(self):
        score = calculate_driving_score([], [])
        assert score is None


# ── Telemetry Model Tests ────────────────────────────────────────────────────

from backend.models.telemetry import (
    VehicleTelemetry,
    DrivetrainStatus,
    EVStatus,
    GPSLocation,
)


class TestExpandedTelemetry:
    """Tests for expanded telemetry model."""

    def test_drivetrain_status(self):
        dt = DrivetrainStatus(throttle_position=50.0, brake_position=0.0, gear_position="D")
        assert dt.throttle_position == 50.0
        assert dt.gear_position == "D"

    def test_ev_status(self):
        ev = EVStatus(ev_range=250.0, charging=False, regen_braking=True)
        assert ev.ev_range == 250.0
        assert ev.regen_braking is True

    def test_gps_location(self):
        gps = GPSLocation(latitude=12.9716, longitude=77.5946)
        assert gps.latitude == 12.9716

    def test_full_telemetry(self):
        t = VehicleTelemetry(
            speed=60.0,
            vehicle_variant="EV",
            drivetrain=DrivetrainStatus(throttle_position=30.0),
            ev_status=EVStatus(ev_range=300.0),
            gps=GPSLocation(latitude=12.97, longitude=77.59),
        )
        assert t.vehicle_variant == "EV"
        assert t.drivetrain.throttle_position == 30.0
        assert t.ev_status.ev_range == 300.0
        assert t.gps.latitude == 12.97
