"""
WebSocket endpoint for real-time telemetry streaming.

Provides a /ws/telemetry WebSocket that pushes live vehicle data
every second while the simulator is running, replacing polling.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)

# Track active connections
_connections: list[WebSocket] = []


@router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    """
    Real-time telemetry WebSocket.

    Pushes JSON telemetry data every second while connected.
    Client can send JSON messages with:
      - {"action": "subscribe"} — start receiving data (default)
      - {"action": "ping"}      — server responds with pong
    """
    await websocket.accept()
    _connections.append(websocket)
    logger.info(f"WebSocket connected ({len(_connections)} active)")

    try:
        while True:
            # Check for client messages (non-blocking)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                msg = json.loads(raw)
                if msg.get("action") == "ping":
                    await websocket.send_json({"action": "pong"})
            except asyncio.TimeoutError:
                pass  # No message — push telemetry below

            # Push current telemetry
            try:
                from backend.services.data_store import DataStore
                store = DataStore()
                t = store.telemetry

                payload = {
                    "type": "telemetry",
                    "data": {
                        "speed": t.speed,
                        "battery_soc": t.battery.soc,
                        "battery_voltage": t.battery.voltage,
                        "battery_temp": t.battery.temperature,
                        "battery_health": t.battery.health_status,
                        "tires": {
                            "front_left": t.tires.front_left,
                            "front_right": t.tires.front_right,
                            "rear_left": t.tires.rear_left,
                            "rear_right": t.tires.rear_right,
                        },
                        "engine_status": t.engine_status,
                        "odometer": t.odometer,
                        "timestamp": t.timestamp,
                        "vehicle_variant": t.vehicle_variant,
                        "throttle": t.drivetrain.throttle_position,
                        "brake": t.drivetrain.brake_position,
                        "gear": t.drivetrain.gear,
                        "ev_range": t.ev_status.ev_range,
                    },
                    "sim_running": store.simulation.running,
                    "alert_count": len(store.alerts),
                }
                await websocket.send_json(payload)
            except Exception as e:
                logger.debug(f"Telemetry push error: {e}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info(f"WebSocket disconnected ({len(_connections)} active)")
