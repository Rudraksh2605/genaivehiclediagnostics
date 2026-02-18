"""
External Simulator Adapter API routes.
Accepts telemetry data from external simulation tools (CARLA, CarMaker, etc.)
and pushes it into the internal data pipeline.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.data_store import DataStore
from backend.models.telemetry import (
    VehicleTelemetry,
    BatteryHealth,
    TireStatus,
    DrivetrainStatus,
    EVStatus,
    GPSLocation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator/external", tags=["External Simulator"])


class ExternalTelemetryFeed(BaseModel):
    """
    CARLA-compatible telemetry data format.
    Fields are optional — provide whatever your simulator outputs.
    """
    speed: Optional[float] = Field(default=None, description="Vehicle speed (km/h)")
    battery_soc: Optional[float] = Field(default=None, description="Battery SoC (%)")
    battery_voltage: Optional[float] = Field(default=None, description="Battery voltage (V)")
    battery_temperature: Optional[float] = Field(default=None, description="Battery temp (°C)")
    tire_fl: Optional[float] = Field(default=None, description="Front-left tire pressure (PSI)")
    tire_fr: Optional[float] = Field(default=None, description="Front-right tire pressure (PSI)")
    tire_rl: Optional[float] = Field(default=None, description="Rear-left tire pressure (PSI)")
    tire_rr: Optional[float] = Field(default=None, description="Rear-right tire pressure (PSI)")
    throttle: Optional[float] = Field(default=None, description="Throttle position (%)")
    brake: Optional[float] = Field(default=None, description="Brake position (%)")
    steering_angle: Optional[float] = Field(default=None, description="Steering angle (deg)")
    gear: Optional[str] = Field(default=None, description="Gear position")
    latitude: Optional[float] = Field(default=None, description="GPS latitude")
    longitude: Optional[float] = Field(default=None, description="GPS longitude")
    ev_range: Optional[float] = Field(default=None, description="EV range (km)")
    odometer: Optional[float] = Field(default=None, description="Odometer (km)")
    vehicle_variant: Optional[str] = Field(default=None, description="EV, Hybrid, or ICE")


@router.post("/feed", summary="Inject telemetry from external simulator")
async def feed_external_telemetry(data: ExternalTelemetryFeed) -> Dict[str, Any]:
    """
    Accept telemetry data from external simulators (CARLA, CarMaker, etc.)
    and inject it into the internal data pipeline.

    All fields are optional — the adapter merges provided values with
    current state, so you can send partial updates.
    """
    store = DataStore()
    current = store.telemetry

    # Merge provided values with current telemetry
    telemetry = VehicleTelemetry(
        timestamp=datetime.utcnow().isoformat(),
        speed=data.speed if data.speed is not None else current.speed,
        battery=BatteryHealth(
            soc=data.battery_soc if data.battery_soc is not None else current.battery.soc,
            voltage=data.battery_voltage if data.battery_voltage is not None else current.battery.voltage,
            temperature=data.battery_temperature if data.battery_temperature is not None else current.battery.temperature,
            health_status=current.battery.health_status,
        ),
        tires=TireStatus(
            front_left=data.tire_fl if data.tire_fl is not None else current.tires.front_left,
            front_right=data.tire_fr if data.tire_fr is not None else current.tires.front_right,
            rear_left=data.tire_rl if data.tire_rl is not None else current.tires.rear_left,
            rear_right=data.tire_rr if data.tire_rr is not None else current.tires.rear_right,
        ),
        drivetrain=DrivetrainStatus(
            throttle_position=data.throttle if data.throttle is not None else current.drivetrain.throttle_position,
            brake_position=data.brake if data.brake is not None else current.drivetrain.brake_position,
            gear_position=data.gear if data.gear is not None else current.drivetrain.gear_position,
            steering_angle=data.steering_angle if data.steering_angle is not None else current.drivetrain.steering_angle,
        ),
        ev_status=EVStatus(
            ev_range=data.ev_range if data.ev_range is not None else current.ev_status.ev_range,
            charging=current.ev_status.charging,
            regen_braking=current.ev_status.regen_braking,
        ),
        gps=GPSLocation(
            latitude=data.latitude if data.latitude is not None else current.gps.latitude,
            longitude=data.longitude if data.longitude is not None else current.gps.longitude,
        ),
        odometer=data.odometer if data.odometer is not None else current.odometer,
        engine_status="running",
        vehicle_variant=data.vehicle_variant if data.vehicle_variant is not None else current.vehicle_variant,
    )

    store.update_telemetry(telemetry)
    logger.info(f"External telemetry injected: speed={telemetry.speed}, soc={telemetry.battery.soc}")

    return {
        "success": True,
        "source": "external_simulator",
        "timestamp": telemetry.timestamp,
        "accepted_fields": {k: v for k, v in data.model_dump().items() if v is not None},
    }


@router.get("/schema", summary="Get expected data format for external feeds")
async def get_feed_schema() -> Dict[str, Any]:
    """
    Return the expected JSON schema for external simulator data feeds.
    Compatible with CARLA, CarMaker, and custom simulators.
    """
    return {
        "description": "CARLA-compatible telemetry feed format",
        "note": "All fields are optional. Send what your simulator provides.",
        "fields": {
            "speed": {"type": "float", "unit": "km/h", "range": "0-200"},
            "battery_soc": {"type": "float", "unit": "%", "range": "0-100"},
            "battery_voltage": {"type": "float", "unit": "V", "range": "0-800"},
            "battery_temperature": {"type": "float", "unit": "°C"},
            "tire_fl": {"type": "float", "unit": "PSI", "range": "0-50"},
            "tire_fr": {"type": "float", "unit": "PSI", "range": "0-50"},
            "tire_rl": {"type": "float", "unit": "PSI", "range": "0-50"},
            "tire_rr": {"type": "float", "unit": "PSI", "range": "0-50"},
            "throttle": {"type": "float", "unit": "%", "range": "0-100"},
            "brake": {"type": "float", "unit": "%", "range": "0-100"},
            "steering_angle": {"type": "float", "unit": "degrees", "range": "-540 to 540"},
            "gear": {"type": "string", "values": ["P", "R", "N", "D"]},
            "latitude": {"type": "float"},
            "longitude": {"type": "float"},
            "ev_range": {"type": "float", "unit": "km", "range": "0-800"},
            "odometer": {"type": "float", "unit": "km"},
            "vehicle_variant": {"type": "string", "values": ["EV", "Hybrid", "ICE"]},
        },
        "example": {
            "speed": 60.0,
            "battery_soc": 85.0,
            "tire_fl": 32.0,
            "throttle": 30.0,
        },
    }
