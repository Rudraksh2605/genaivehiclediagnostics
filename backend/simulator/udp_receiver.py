"""
UDP Receiver Protocol for high-frequency external Vehicle Simulators.
Simulators like CARLA often push raw telemetry over UDP to avoid TCP/HTTP overhead.
This file implements an asyncio DatagramProtocol that parses incoming JSON payloads
and injects them directly into the internal DataStore.
"""

import asyncio
import json
import logging
from datetime import datetime

from backend.services.data_store import DataStore
from backend.api.external_sim_routes import ExternalTelemetryFeed
from backend.models.telemetry import (
    VehicleTelemetry,
    BatteryHealth,
    TireStatus,
    DrivetrainStatus,
    EVStatus,
    GPSLocation,
)

logger = logging.getLogger(__name__)

class TelemetryUDPProtocol(asyncio.DatagramProtocol):
    """Async UDP Protocol for receiving JSON telemetry."""
    
    def __init__(self):
        self.store = DataStore()
        
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Telemetry Receiver bound to {transport.get_extra_info('sockname')}")
        
    def datagram_received(self, data: bytes, addr):
        """Handle incoming UDP packets."""
        try:
            # 1. Decode UTF-8 JSON
            payload = data.decode('utf-8')
            data_dict = json.loads(payload)
            
            # 2. Parse using the same schema used by REST and WebSockets
            feed_data = ExternalTelemetryFeed(**data_dict)
            current = self.store.telemetry
            
            # 3. Merge received data with current system state
            telemetry = VehicleTelemetry(
                timestamp=datetime.utcnow().isoformat(),
                speed=feed_data.speed if feed_data.speed is not None else current.speed,
                battery=BatteryHealth(
                    soc=feed_data.battery_soc if feed_data.battery_soc is not None else current.battery.soc,
                    voltage=feed_data.battery_voltage if feed_data.battery_voltage is not None else current.battery.voltage,
                    temperature=feed_data.battery_temperature if feed_data.battery_temperature is not None else current.battery.temperature,
                    health_status=current.battery.health_status,
                ),
                tires=TireStatus(
                    front_left=feed_data.tire_fl if feed_data.tire_fl is not None else current.tires.front_left,
                    front_right=feed_data.tire_fr if feed_data.tire_fr is not None else current.tires.front_right,
                    rear_left=feed_data.tire_rl if feed_data.tire_rl is not None else current.tires.rear_left,
                    rear_right=feed_data.tire_rr if feed_data.tire_rr is not None else current.tires.rear_right,
                ),
                drivetrain=DrivetrainStatus(
                    throttle_position=feed_data.throttle if feed_data.throttle is not None else current.drivetrain.throttle_position,
                    brake_position=feed_data.brake if feed_data.brake is not None else current.drivetrain.brake_position,
                    gear_position=feed_data.gear if feed_data.gear is not None else current.drivetrain.gear_position,
                    steering_angle=feed_data.steering_angle if feed_data.steering_angle is not None else current.drivetrain.steering_angle,
                ),
                ev_status=EVStatus(
                    ev_range=feed_data.ev_range if feed_data.ev_range is not None else current.ev_status.ev_range,
                    charging=current.ev_status.charging,
                    regen_braking=current.ev_status.regen_braking,
                ),
                gps=GPSLocation(
                    latitude=feed_data.latitude if feed_data.latitude is not None else current.gps.latitude,
                    longitude=feed_data.longitude if feed_data.longitude is not None else current.gps.longitude,
                ),
                odometer=feed_data.odometer if feed_data.odometer is not None else current.odometer,
                engine_status="running",
                vehicle_variant=feed_data.vehicle_variant if feed_data.vehicle_variant is not None else current.vehicle_variant,
            )
            
            # 4. Inject into the pipeline
            self.store.update_telemetry(telemetry)
            
        except json.JSONDecodeError:
            logger.warning(f"UDP Receiver: Invalid JSON payload received from {addr}")
        except Exception as e:
            logger.warning(f"UDP Receiver error from {addr}: {e}")

async def start_udp_receiver(host: str = "0.0.0.0", port: int = 9000):
    """Start the UDP server as a background task."""
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: TelemetryUDPProtocol(),
        local_addr=(host, port)
    )
    return transport
