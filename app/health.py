from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.database.connection import DatabaseConnection
from app.settings import Settings
from app.state_store import StateStore


class HealthMonitor:
    def __init__(self, settings: Settings, database: DatabaseConnection, state_store: StateStore) -> None:
        self.settings = settings
        self.database = database
        self.state_store = state_store
        self.status = "NOT_READY"
        self.startup_time = datetime.now(timezone.utc).isoformat()
        self.last_heartbeat = self.startup_time
        self.last_failure_reason = ""

    def record_startup(self) -> Dict[str, Any]:
        payload = self.snapshot()
        self.state_store.set("health", payload)
        return payload

    def snapshot(self) -> Dict[str, Any]:
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        payload = {
            "status": self.status,
            "startup_time": self.startup_time,
            "last_heartbeat": self.last_heartbeat,
            "last_failure_reason": self.last_failure_reason,
            "database": self.database.connect().execute("SELECT 1").fetchone() is not None,
            "paper_mode": self.settings.is_paper_mode,
            "execution_mode": "paper" if self.settings.is_paper_mode else self.settings.trading_mode,
            "configured_primary_broker": "fyers",
            "active_execution_broker": "paper" if self.settings.is_paper_mode else self.settings.primary_broker,
            "standby_broker": "dhan",
        }
        self.state_store.set("health", payload)
        return payload
