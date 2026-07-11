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
        self.status = "READY"
        payload = self.snapshot()
        self.state_store.set("health", payload)
        return payload

    def record_shutdown(self) -> Dict[str, Any]:
        self.status = "STOPPED"
        payload = self.snapshot()
        self.state_store.set("health", payload)
        return payload

    def snapshot(self) -> Dict[str, Any]:
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()
        universe_status = self.state_store.get("universe_status") or {}
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
            "universe": {
                "ready": universe_status.get("ready", False),
                "conflict_count": universe_status.get("conflict_count", 0),
                "last_import_time": universe_status.get("last_import_time"),
                "import_source": universe_status.get("import_source", "NOT_CONFIGURED"),
            },
            "market_data": {
                "market_data_mode": (self.state_store.get("market_data_status") or {}).get("market_data_mode", "not_ready"),
                "primary_market_data_broker": (self.state_store.get("market_data_status") or {}).get("primary_market_data_broker", "fyers"),
                "standby_market_data_broker": (self.state_store.get("market_data_status") or {}).get("standby_market_data_broker", "dhan"),
                "active_market_data_source": (self.state_store.get("market_data_status") or {}).get("active_market_data_source", "fixture"),
                "primary_connection_state": (self.state_store.get("market_data_status") or {}).get("primary_connection_state", "NOT_READY"),
                "standby_connection_state": (self.state_store.get("market_data_status") or {}).get("standby_connection_state", "NOT_READY"),
                "last_valid_tick": ((self.state_store.get("market_data_status") or {}).get("heartbeat") or {}).get("last_valid_tick"),
                "quote_cache_size": (self.state_store.get("market_data_status") or {}).get("quote_cache_size", 0),
                "active_subscriptions": (self.state_store.get("market_data_status") or {}).get("active_subscriptions", 0),
                "stale_instruments": (self.state_store.get("market_data_status") or {}).get("stale_instruments", 0),
                "reconnect_count": ((self.state_store.get("market_data_status") or {}).get("heartbeat") or {}).get("reconnect_count", 0),
                "candle_builder_state": (self.state_store.get("market_data_status") or {}).get("candle_builder_state", "NOT_READY"),
            },
        }
        self.state_store.set("health", payload)
        return payload
