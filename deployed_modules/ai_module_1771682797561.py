import threading
import time
import random
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

class SpeedThresholds(BaseModel):
    max_speed_kmh: float

class SpeedData(BaseModel):
    current_speed_kmh: float

class AlertStatus(BaseModel):
    alert_active: bool
    exceeded_speed_kmh: Optional[float] = None
    threshold_kmh: Optional[float] = None

class ServiceStatus(BaseModel):
    is_running: bool

class SpeedMonitorService:
    def __init__(self):
        self._current_speed: float = 0.0
        self._alert_active: bool = False
        self._exceeded_speed: Optional[float] = None
        self._thresholds: SpeedThresholds = SpeedThresholds(max_speed_kmh=100.0)
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()

    def _simulate_can_bus_speed(self) -> float:
        return random.uniform(0, 150)

    def _monitor_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                speed = self._simulate_can_bus_speed()
                self._current_speed = speed
                if speed > self._thresholds.max_speed_kmh:
                    self._alert_active = True
                    self._exceeded_speed = speed
                else:
                    self._alert_active = False
                    self._exceeded_speed = None
            time.sleep(1)

    def start(self) -> bool:
        with self._lock:
            if not self._running:
                self._running = True
                self._monitor_thread = threading.Thread(target=self._monitor_loop)
                self._monitor_thread.daemon = True
                self._monitor_thread.start()
                return True
            return False

    def stop(self) -> bool:
        with self._lock:
            if self._running:
                self._running = False
                return True
            return False

    def get_service_status(self) -> ServiceStatus:
        with self._lock:
            return ServiceStatus(is_running=self._running)

    def get_current_speed(self) -> SpeedData:
        with self._lock:
            return SpeedData(current_speed_kmh=self._current_speed)

    def get_alert_status(self) -> AlertStatus:
        with self._lock:
            if self._alert_active:
                return AlertStatus(
                    alert_active=True,
                    exceeded_speed_kmh=self._exceeded_speed,
                    threshold_kmh=self._thresholds.max_speed_kmh
                )
            return AlertStatus(alert_active=False)

    def set_thresholds(self, new_thresholds: SpeedThresholds) -> SpeedThresholds:
        with self._lock:
            self._thresholds = new_thresholds
            return self._thresholds

    def get_thresholds(self) -> SpeedThresholds:
        with self._lock:
            return self._thresholds

app = FastAPI()
monitor_service = SpeedMonitorService()

@app.post("/monitor/start", response_model=ServiceStatus)
def start_monitor_service() -> ServiceStatus:
    if monitor_service.start():
        return ServiceStatus(is_running=True)
    raise HTTPException(status_code=409, detail="Monitor service is already running")

@app.post("/monitor/stop", response_model=ServiceStatus)
def stop_monitor_service() -> ServiceStatus:
    if monitor_service.stop():
        return ServiceStatus(is_running=False)
    raise HTTPException(status_code=409, detail="Monitor service is not running")

@app.get("/monitor/status", response_model=ServiceStatus)
def get_monitor_status() -> ServiceStatus:
    return monitor_service.get_service_status()

@app.get("/speed", response_model=SpeedData)
def get_speed() -> SpeedData:
    return monitor_service.get_current_speed()

@app.get("/alert", response_model=AlertStatus)
def get_alert() -> AlertStatus:
    return monitor_service.get_alert_status()

@app.put("/thresholds", response_model=SpeedThresholds)
def update_thresholds(thresholds: SpeedThresholds) -> SpeedThresholds:
    return monitor_service.set_thresholds(thresholds)

@app.get("/thresholds", response_model=SpeedThresholds)
def get_thresholds() -> SpeedThresholds:
    return monitor_service.get_thresholds()