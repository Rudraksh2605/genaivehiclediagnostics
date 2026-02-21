"""
Tests for Vehicle Simulator — variant behavior and telemetry generation.
Uses the FastAPI TestClient for synchronous testing.
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestSimulatorLifecycle:
    """Tests for simulator start/stop via API."""

    def test_start_simulation(self):
        res = client.post("/vehicle/simulate/start?variant=EV")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "started" or "running" in str(data).lower()

    def test_stop_simulation(self):
        # Start first
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(0.5)
        res = client.post("/vehicle/simulate/stop")
        assert res.status_code == 200

    def test_simulation_status_changes(self):
        """Ensure starting sim changes telemetry."""
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(2)  # Let simulator generate data
        res = client.get("/vehicle/all")
        assert res.status_code == 200
        data = res.json()
        assert "speed" in data
        assert "battery" in data
        client.post("/vehicle/simulate/stop")


class TestVariantBehavior:
    """Tests for EV/ICE/Hybrid variant-specific behavior."""

    def test_ev_variant(self):
        res = client.post("/vehicle/simulate/start?variant=EV")
        assert res.status_code == 200
        time.sleep(1.5)
        tel = client.get("/vehicle/all").json()
        assert "battery" in tel
        assert tel["battery"]["soc"] is not None
        client.post("/vehicle/simulate/stop")

    def test_ice_variant(self):
        res = client.post("/vehicle/simulate/start?variant=ICE")
        assert res.status_code == 200
        time.sleep(1.5)
        tel = client.get("/vehicle/all").json()
        assert "speed" in tel
        client.post("/vehicle/simulate/stop")

    def test_hybrid_variant(self):
        res = client.post("/vehicle/simulate/start?variant=Hybrid")
        assert res.status_code == 200
        time.sleep(1.5)
        tel = client.get("/vehicle/all").json()
        assert "battery" in tel
        assert "speed" in tel
        client.post("/vehicle/simulate/stop")


class TestTelemetryBounds:
    """Tests for telemetry values within expected bounds."""

    def test_speed_within_bounds(self):
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(2)
        tel = client.get("/vehicle/all").json()
        assert 0 <= tel["speed"] <= 240
        client.post("/vehicle/simulate/stop")

    def test_battery_soc_within_bounds(self):
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(2)
        tel = client.get("/vehicle/all").json()
        assert 0 <= tel["battery"]["soc"] <= 100
        client.post("/vehicle/simulate/stop")

    def test_tire_pressure_within_bounds(self):
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(2)
        tel = client.get("/vehicle/all").json()
        tires = tel["tires"]
        for key in ["front_left", "front_right", "rear_left", "rear_right"]:
            assert 20 <= tires[key] <= 45
        client.post("/vehicle/simulate/stop")


class TestTelemetryHistory:
    """Tests for telemetry history via API."""

    def test_history_populates(self):
        client.post("/vehicle/simulate/start?variant=EV")
        # Force an extra tick because TestClient sync sleep might block background async tasks
        from backend.simulator.vehicle_simulator import get_simulator
        sim = get_simulator()
        sim.store.update_telemetry(sim._generate_telemetry())
        
        res = client.get("/vehicle/history")
        assert res.status_code == 200
        data = res.json()
        # History endpoint returns {"count": N, "history": [...]}
        assert "history" in data
        assert isinstance(data["history"], list)
        assert len(data["history"]) >= 2
        client.post("/vehicle/simulate/stop")

    def test_history_entry_structure(self):
        client.post("/vehicle/simulate/start?variant=EV")
        time.sleep(2)
        data = client.get("/vehicle/history").json()
        history = data.get("history", [])
        if len(history) > 0:
            entry = history[0]
            assert "speed" in entry
            assert "battery_soc" in entry
        client.post("/vehicle/simulate/stop")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
