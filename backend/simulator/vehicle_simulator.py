"""
Vehicle Data Simulation Engine.
Generates realistic vehicle telemetry data every 1 second using asyncio.
Supports start/stop via API and pushes data to the in-memory data store.

Simulated signals:
- Speed, Battery SoC, Tire Pressure (original)
- Throttle, Brake, Gear, Steering, EV Range, GPS (new)
"""

import asyncio
import math
import random
import logging
import uuid
from datetime import datetime
from typing import Optional

from backend.models.telemetry import (
    VehicleTelemetry,
    BatteryHealth,
    TireStatus,
    DrivetrainStatus,
    EVStatus,
    GPSLocation,
    SimulationStatus,
)
from backend.services.data_store import DataStore
from backend.analytics.health_analyzer import HealthAnalyzer

logger = logging.getLogger(__name__)


class VehicleSimulator:
    """
    Async vehicle data simulator.
    Generates realistic telemetry with:
    - Speed: 0-140 km/h dynamic variation with acceleration/deceleration
    - Battery SoC: slow gradual decline with occasional rapid drops
    - Tire pressure: normal range with occasional sudden drop events
    - Throttle/Brake: correlated with speed changes
    - Gear: automatic shifting based on speed
    - Steering: smooth random variation
    - EV Range: derived from battery SoC and driving pattern
    - GPS: simulated driving route
    """

    def __init__(self) -> None:
        self.store = DataStore()
        self.analyzer = HealthAnalyzer()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._tick_count = 0
        self._variant = "EV"  # EV, Hybrid, ICE

        # Simulation state variables — original
        self._speed = 0.0
        self._battery_soc = 95.0
        self._battery_voltage = 400.0
        self._battery_temp = 25.0
        self._tire_fl = 32.0
        self._tire_fr = 31.5
        self._tire_rl = 31.8
        self._tire_rr = 32.2
        self._odometer = 15000.0
        self._speed_direction = 1  # 1 = accelerating, -1 = decelerating
        self._fuel_level = 100.0  # ICE/Hybrid fuel %

        # New signal state variables
        self._throttle = 0.0
        self._brake = 0.0
        self._gear = "P"
        self._steering = 0.0
        self._ev_range = 350.0
        self._gps_lat = 12.9716       # Bengaluru, India (default start)
        self._gps_lon = 77.5946
        self._gps_heading = 0.0       # radians

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self, variant: str = "EV") -> SimulationStatus:
        """Start the simulation background task."""
        if self._running:
            return SimulationStatus(
                running=True,
                tick_count=self._tick_count,
                start_time=self.store.simulation.start_time,
                message="Simulator already running",
            )

        self._variant = variant.upper() if variant else "EV"
        self.store.vehicle_variant = self._variant
        self._running = True
        self._tick_count = 0
        start_time = datetime.utcnow().isoformat()

        # Reset ICE-specific state
        if self._variant == "ICE":
            self._battery_soc = 100.0  # Starter battery, stays stable
            self._fuel_level = 100.0

        self.store.simulation = SimulationStatus(
            running=True,
            tick_count=0,
            start_time=start_time,
            message=f"Simulator started (variant: {self._variant})",
        )

        self._task = asyncio.create_task(self._simulation_loop())
        logger.info(f"Vehicle simulator started (variant={self._variant})")

        return self.store.simulation

    async def stop(self) -> SimulationStatus:
        """Stop the simulation background task."""
        if not self._running:
            return SimulationStatus(
                running=False,
                tick_count=self._tick_count,
                message="Simulator not running",
            )

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self.store.simulation = SimulationStatus(
            running=False,
            tick_count=self._tick_count,
            message=f"Simulator stopped after {self._tick_count} ticks",
        )

        logger.info(f"Vehicle simulator stopped after {self._tick_count} ticks")
        return self.store.simulation

    async def _simulation_loop(self) -> None:
        """Main simulation loop — generates data every 1 second."""
        logger.info("Simulation loop started")
        try:
            while self._running:
                self._tick_count += 1
                telemetry = self._generate_telemetry()

                # Update data store
                self.store.update_telemetry(telemetry)

                # Run analytics on the new telemetry
                new_alerts = self.analyzer.analyze(telemetry, self.store)
                for alert in new_alerts:
                    self.store.add_alert(alert)

                # Update simulation status
                self.store.simulation.tick_count = self._tick_count

                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled")
            raise

    def _generate_telemetry(self) -> VehicleTelemetry:
        """Generate a single telemetry snapshot with realistic variations."""

        # --- Speed simulation ---
        if random.random() < 0.05:
            self._speed_direction *= -1

        speed_delta = random.uniform(1.0, 5.0) * self._speed_direction
        self._speed = max(0, min(140, self._speed + speed_delta))

        # Occasionally hold high speed for alert testing
        if self._tick_count % 50 < 15 and self._tick_count > 20:
            self._speed = random.uniform(105, 130)

        # --- Throttle & Brake (correlated with speed changes) ---
        if speed_delta > 0:
            self._throttle = min(100, abs(speed_delta) * 15 + random.uniform(0, 10))
            self._brake = 0.0
        else:
            self._throttle = 0.0
            self._brake = min(100, abs(speed_delta) * 12 + random.uniform(0, 8))

        # Occasional harsh braking event
        if random.random() < 0.015:
            self._brake = random.uniform(85, 100)
            self._throttle = 0.0

        # --- Gear simulation (automatic based on speed) ---
        if self._speed < 1:
            self._gear = "P"
        elif self._speed < 20:
            self._gear = "D"  # 1st effective range
        elif self._speed < 40:
            self._gear = "D"
        elif self._speed < 60:
            self._gear = "D"
        elif self._speed < 80:
            self._gear = "D"
        else:
            self._gear = "D"
        # Show numbered gears occasionally
        if self._speed > 5 and random.random() < 0.02:
            self._gear = random.choice(["1", "2", "3"])

        # --- Steering simulation (smooth random) ---
        steering_delta = random.uniform(-10, 10)
        self._steering += steering_delta
        self._steering = max(-540, min(540, self._steering))
        # Tend back to center
        self._steering *= 0.95

        # --- Battery simulation (variant-aware) ---
        if self._variant == "ICE":
            # ICE: starter battery stays stable (12V system)
            self._battery_soc = max(90, 100 - random.uniform(0, 0.01) * self._tick_count)
            self._battery_voltage = 12.0 + (self._battery_soc / 100) * 2
            self._battery_temp = 25 + random.uniform(-2, 3)
            self._ev_range = 0.0
            regen = False
            # Fuel consumption
            self._fuel_level -= random.uniform(0.02, 0.1)
            self._fuel_level = max(0, self._fuel_level)
        elif self._variant == "Hybrid":
            # Hybrid: slower battery drain, fuel assists
            self._battery_soc -= random.uniform(0.02, 0.08)
            if random.random() < 0.01:
                self._battery_soc -= random.uniform(2.0, 4.0)
            self._battery_soc = max(15.0, min(100.0, self._battery_soc))
            self._battery_voltage = 350 + (self._battery_soc / 100) * 50
            self._battery_temp = 25 + random.uniform(-2, 5)
            efficiency = 4.0 - (self._speed / 120)
            self._ev_range = max(0, self._battery_soc * efficiency)
            regen = self._brake > 30
            self._fuel_level -= random.uniform(0.01, 0.05)
            self._fuel_level = max(0, self._fuel_level)
        else:
            # EV: original behavior
            self._battery_soc -= random.uniform(0.05, 0.2)
            if random.random() < 0.02:
                self._battery_soc -= random.uniform(5.0, 8.0)
                logger.debug("Battery rapid drop event triggered")
            self._battery_soc = max(5.0, min(100.0, self._battery_soc))
            self._battery_voltage = 350 + (self._battery_soc / 100) * 50
            self._battery_temp = 25 + random.uniform(-2, 5)
            efficiency = 5.5 - (self._speed / 100)
            self._ev_range = max(0, self._battery_soc * efficiency)
            regen = self._brake > 30

        health_status = "Good"
        if self._battery_soc < 20:
            health_status = "Low"
        elif self._battery_soc < 50:
            health_status = "Fair"

        # --- Tire pressure simulation ---
        self._tire_fl += random.uniform(-0.1, 0.1)
        self._tire_fr += random.uniform(-0.1, 0.1)
        self._tire_rl += random.uniform(-0.1, 0.1)
        self._tire_rr += random.uniform(-0.1, 0.1)

        if random.random() < 0.01:
            tire_choice = random.choice(["fl", "fr", "rl", "rr"])
            drop = random.uniform(8, 15)
            if tire_choice == "fl":
                self._tire_fl -= drop
            elif tire_choice == "fr":
                self._tire_fr -= drop
            elif tire_choice == "rl":
                self._tire_rl -= drop
            else:
                self._tire_rr -= drop
            logger.debug(f"Tire pressure sudden drop on {tire_choice}")

        self._tire_fl = max(15.0, min(40.0, self._tire_fl))
        self._tire_fr = max(15.0, min(40.0, self._tire_fr))
        self._tire_rl = max(15.0, min(40.0, self._tire_rl))
        self._tire_rr = max(15.0, min(40.0, self._tire_rr))

        # --- GPS simulation (small movements) ---
        self._gps_heading += random.uniform(-0.1, 0.1)
        speed_m_s = self._speed / 3.6
        self._gps_lat += (speed_m_s * math.cos(self._gps_heading)) / 111320
        self._gps_lon += (speed_m_s * math.sin(self._gps_heading)) / (
            111320 * math.cos(math.radians(self._gps_lat))
        )

        # --- Odometer ---
        self._odometer += (self._speed / 3600)

        return VehicleTelemetry(
            timestamp=datetime.utcnow().isoformat(),
            speed=round(self._speed, 1),
            battery=BatteryHealth(
                soc=round(self._battery_soc, 1),
                voltage=round(self._battery_voltage, 1),
                temperature=round(self._battery_temp, 1),
                health_status=health_status,
            ),
            tires=TireStatus(
                front_left=round(self._tire_fl, 1),
                front_right=round(self._tire_fr, 1),
                rear_left=round(self._tire_rl, 1),
                rear_right=round(self._tire_rr, 1),
            ),
            drivetrain=DrivetrainStatus(
                throttle_position=round(self._throttle, 1),
                brake_position=round(self._brake, 1),
                gear_position=self._gear,
                steering_angle=round(self._steering, 1),
            ),
            ev_status=EVStatus(
                ev_range=round(self._ev_range, 1),
                charging=False,
                regen_braking=regen,
            ),
            gps=GPSLocation(
                latitude=round(self._gps_lat, 6),
                longitude=round(self._gps_lon, 6),
            ),
            odometer=round(self._odometer, 1),
            engine_status="running" if self._variant == "ICE" else "motor_running",
            vehicle_variant=self._variant,
        )


# Module-level singleton
_simulator: Optional[VehicleSimulator] = None


def get_simulator() -> VehicleSimulator:
    """Get or create the singleton simulator instance."""
    global _simulator
    if _simulator is None:
        _simulator = VehicleSimulator()
    return _simulator
