"""
SQLite Persistence Layer for Vehicle Diagnostics.

Persists telemetry snapshots and alerts to a local SQLite database,
allowing data to survive server restarts. Models are already persisted
via joblib in backend/ml/saved_models/.
"""

import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Database file location
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)
DB_PATH = os.path.join(DATA_DIR, "vehicle_diagnostics.db")


class PersistenceManager:
    """SQLite-based persistence for telemetry and alerts."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS telemetry_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    speed REAL,
                    battery_soc REAL,
                    battery_voltage REAL,
                    battery_temp REAL,
                    tire_fl REAL,
                    tire_fr REAL,
                    tire_rl REAL,
                    tire_rr REAL,
                    throttle REAL,
                    brake REAL,
                    ev_range REAL,
                    engine_status TEXT,
                    vehicle_variant TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT,
                    severity TEXT,
                    signal TEXT,
                    message TEXT,
                    value REAL,
                    threshold REAL,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_ts ON telemetry_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);
            """)
            conn.commit()
            logger.info(f"Persistence DB initialized at {self.db_path}")
        finally:
            conn.close()

    def save_telemetry(self, snapshot: Dict[str, Any]) -> None:
        """Save a single telemetry snapshot."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO telemetry_log 
                    (timestamp, speed, battery_soc, battery_voltage, battery_temp,
                     tire_fl, tire_fr, tire_rl, tire_rr, throttle, brake,
                     ev_range, engine_status, vehicle_variant)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.get("timestamp", datetime.utcnow().isoformat()),
                snapshot.get("speed", 0),
                snapshot.get("battery_soc", 0),
                snapshot.get("battery_voltage", 0),
                snapshot.get("battery_temp", 0),
                snapshot.get("tire_fl", 0),
                snapshot.get("tire_fr", 0),
                snapshot.get("tire_rl", 0),
                snapshot.get("tire_rr", 0),
                snapshot.get("throttle", 0),
                snapshot.get("brake", 0),
                snapshot.get("ev_range", 0),
                snapshot.get("engine_status", ""),
                snapshot.get("vehicle_variant", "EV"),
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving telemetry: {e}")
        finally:
            conn.close()

    def save_alert(self, alert_data: Dict[str, Any]) -> None:
        """Save an alert record."""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO alerts 
                    (timestamp, alert_type, severity, signal, message, value, threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_data.get("timestamp", datetime.utcnow().isoformat()),
                alert_data.get("alert_type", ""),
                alert_data.get("severity", ""),
                alert_data.get("signal", ""),
                alert_data.get("message", ""),
                alert_data.get("value"),
                alert_data.get("threshold"),
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
        finally:
            conn.close()

    def load_telemetry_history(self, limit: int = 300) -> List[Dict[str, Any]]:
        """Load last N telemetry snapshots."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM telemetry_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            result = [dict(r) for r in reversed(rows)]
            return result
        except Exception as e:
            logger.error(f"Error loading telemetry: {e}")
            return []
        finally:
            conn.close()

    def load_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Load last N alerts."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error loading alerts: {e}")
            return []
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        conn = self._get_conn()
        try:
            t_count = conn.execute("SELECT COUNT(*) FROM telemetry_log").fetchone()[0]
            a_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            return {
                "telemetry_records": t_count,
                "alert_records": a_count,
                "database_size_bytes": db_size,
                "database_path": self.db_path,
            }
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def cleanup(self, keep_last_hours: int = 24) -> int:
        """Remove records older than N hours."""
        conn = self._get_conn()
        try:
            cutoff = f"datetime('now', '-{keep_last_hours} hours')"
            cur = conn.execute(f"DELETE FROM telemetry_log WHERE created_at < {cutoff}")
            deleted = cur.rowcount
            conn.execute(f"DELETE FROM alerts WHERE created_at < {cutoff}")
            conn.commit()
            return deleted
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0
        finally:
            conn.close()


# Singleton
_manager: Optional[PersistenceManager] = None


def get_persistence() -> PersistenceManager:
    global _manager
    if _manager is None:
        _manager = PersistenceManager()
    return _manager
