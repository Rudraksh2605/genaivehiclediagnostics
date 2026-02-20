"""
GenAI-Assisted Vehicle Health & Diagnostics — Backend Entry Point.

FastAPI application that serves:
- Vehicle telemetry REST APIs
- Data simulation control
- Health analytics & alerts
- OTA signal configuration
- Development traceability mapping
"""

import logging
import json
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.vehicle_routes import router as vehicle_router
from backend.api.simulation_routes import router as simulation_router
from backend.api.traceability_routes import router as traceability_router
from backend.api.config_routes import router as config_router
from backend.api.codegen_routes import router as codegen_router
from backend.api.compliance_routes import router as compliance_router
from backend.api.predictive_routes import router as predictive_router
from backend.api.ml_routes import router as ml_router
from backend.api.history_routes import router as history_router
from backend.api.ota_routes import router as ota_router
from backend.api.external_sim_routes import router as external_sim_router
from backend.api.ws_routes import router as ws_router

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vehicle Health & Diagnostics API",
    description=(
        "GenAI-Assisted Development of Vehicle Health & Diagnostics "
        "for Software Defined Vehicles. Provides real-time vehicle "
        "telemetry, health analytics, alerts, simulation control, "
        "multi-language code generation, and MISRA compliance checking."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(vehicle_router)
app.include_router(simulation_router)
app.include_router(traceability_router)
app.include_router(config_router)
app.include_router(codegen_router)
app.include_router(compliance_router)
app.include_router(predictive_router)
app.include_router(ml_router)
app.include_router(history_router)
app.include_router(ota_router)
app.include_router(external_sim_router)
app.include_router(ws_router)

# ── Static Files (Web Dashboard) ────────────────────────────────────────────
_dashboard_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web-dashboard",
)
if os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")


# ── Root & Health ────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    """API root — returns service info."""
    return {
        "service": "Vehicle Health & Diagnostics API",
        "version": "2.0.0",
        "status": "operational",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "endpoints": {
            "vehicle": "/vehicle/all",
            "speed": "/vehicle/speed",
            "battery": "/vehicle/battery",
            "tire_pressure": "/vehicle/tire-pressure",
            "alerts": "/vehicle/alerts",
            "simulate_start": "/vehicle/simulate/start",
            "simulate_stop": "/vehicle/simulate/stop",
            "simulate_status": "/vehicle/simulate/status",
            "traceability": "/traceability/map",
            "config": "/config/signals",
            "codegen": "/codegen/generate",
            "codegen_all": "/codegen/generate-all",
            "design": "/codegen/design",
            "test_gen": "/codegen/test",
            "llm_compare": "/codegen/compare-llms",
            "compliance_check": "/compliance/check",
            "compliance_rules": "/compliance/rules",
            "predictive_analysis": "/predictive/analysis",
            "ml_train": "/ml/train",
            "ml_predict": "/ml/predict",
            "ml_status": "/ml/status",
            "ml_gpu_info": "/ml/gpu",
            "telemetry_history": "/vehicle/history",
            "ota_deploy": "/ota/deploy",
            "ota_history": "/ota/history",
            "ota_status": "/ota/status",
            "external_sim_feed": "/simulator/external/feed",
            "external_sim_schema": "/simulator/external/schema",
        },
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ── Startup Event ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("=" * 60)
    logger.info("Vehicle Health & Diagnostics API starting up")
    logger.info("=" * 60)

    # Pre-initialize the data store (loads config)
    from backend.services.data_store import DataStore
    store = DataStore()
    logger.info(f"Loaded {len(store.signal_configs)} signal configurations")
    logger.info("API documentation available at /docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down — stopping simulator if running")
    from backend.simulator.vehicle_simulator import get_simulator
    simulator = get_simulator()
    if simulator.is_running:
        await simulator.stop()
    logger.info("Shutdown complete")
