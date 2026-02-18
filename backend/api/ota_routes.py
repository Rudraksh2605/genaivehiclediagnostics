"""
OTA (Over-The-Air) Update Simulation API routes.
Simulates deploying new configurations, signal definitions, or code modules
to a running vehicle system at runtime.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.data_store import DataStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ota", tags=["OTA Updates"])


class OTADeployRequest(BaseModel):
    """Request to deploy an OTA update."""
    update_type: str = Field(
        ...,
        description="Type: signal_config, code_module, parameter_update"
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Update payload (config data, module definition, etc.)"
    )
    description: str = Field(
        default="",
        description="Human-readable description of the update"
    )


@router.post("/deploy", summary="Deploy an OTA update")
async def deploy_ota_update(req: OTADeployRequest) -> Dict[str, Any]:
    """
    Simulate deploying an OTA update to the vehicle system.

    Supports:
    - signal_config: Add/modify signal definitions
    - code_module: Deploy new diagnostic module
    - parameter_update: Update system parameters
    """
    store = DataStore()
    store.ota_version += 1

    update_record = {
        "version": store.ota_version,
        "update_type": req.update_type,
        "payload": req.payload,
        "description": req.description or f"OTA update v{store.ota_version}",
        "status": "deployed",
        "deployed_at": datetime.utcnow().isoformat(),
    }

    # Apply the update based on type
    if req.update_type == "signal_config":
        # Add new signal to the config
        from backend.models.telemetry import SignalConfig
        try:
            new_signal = SignalConfig(**req.payload)
            store.signal_configs.append(new_signal)
            update_record["applied"] = f"Signal '{new_signal.name}' added"
        except Exception:
            update_record["applied"] = "Signal config stored (partial schema)"

    elif req.update_type == "parameter_update":
        update_record["applied"] = "Parameters updated in runtime config"

    elif req.update_type == "code_module":
        update_record["applied"] = "Module registered for next diagnostic cycle"

    else:
        update_record["applied"] = "Custom update stored"

    store.ota_history.append(update_record)
    logger.info(f"OTA Update v{store.ota_version} deployed: {req.update_type}")

    return {
        "success": True,
        "version": store.ota_version,
        "update": update_record,
    }


@router.get("/history", summary="Get OTA update history")
async def get_ota_history() -> Dict[str, Any]:
    """Return the history of all OTA updates deployed to this session."""
    store = DataStore()
    return {
        "current_version": store.ota_version,
        "total_updates": len(store.ota_history),
        "history": list(reversed(store.ota_history)),
    }


@router.get("/status", summary="Get current OTA status")
async def get_ota_status() -> Dict[str, Any]:
    """Return the current system version and last update info."""
    store = DataStore()
    last_update = store.ota_history[-1] if store.ota_history else None
    return {
        "current_version": store.ota_version,
        "total_updates": len(store.ota_history),
        "last_update": last_update,
    }
