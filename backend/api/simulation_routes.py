"""
Simulation control API routes.
Endpoints to start, stop, and check status of the vehicle data simulator.
"""

from fastapi import APIRouter, Query

from backend.simulator.vehicle_simulator import get_simulator
from backend.models.telemetry import SimulationStatus

router = APIRouter(prefix="/vehicle/simulate", tags=["Simulation"])


@router.post("/start", summary="Start vehicle data simulation")
async def start_simulation(
    variant: str = Query(default="EV", description="Vehicle variant: EV, Hybrid, ICE")
) -> SimulationStatus:
    """Start generating simulated vehicle telemetry data."""
    simulator = get_simulator()
    return await simulator.start(variant=variant)


@router.post("/stop", summary="Stop vehicle data simulation")
async def stop_simulation() -> SimulationStatus:
    """Stop the vehicle data simulation."""
    simulator = get_simulator()
    return await simulator.stop()


@router.get("/status", summary="Get simulation status")
async def get_simulation_status() -> SimulationStatus:
    """Check whether the simulator is currently running."""
    simulator = get_simulator()
    return simulator.store.simulation
