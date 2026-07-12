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
        broker_readiness = self.state_store.get("broker_readiness") or {}
        market_data_status = self.state_store.get("market_data_status") or {}
        payload = {
            "status": self.status,
            "startup_time": self.startup_time,
            "last_heartbeat": self.last_heartbeat,
            "last_failure_reason": self.last_failure_reason,
            "database": self.database.connect().execute("SELECT 1").fetchone() is not None,
            "paper_mode": self.settings.is_paper_mode,
            "execution_mode": "paper" if self.settings.is_paper_mode else self.settings.trading_mode,
            "market_data_mode": self.settings.market_data_mode.lower(),
            "configured_primary_broker": self.settings.primary_broker,
            "active_execution_broker": "paper" if self.settings.is_paper_mode else self.settings.execution_broker,
            "standby_broker": self.settings.standby_broker,
            "universe": {
                "ready": universe_status.get("ready", False),
                "conflict_count": universe_status.get("conflict_count", 0),
                "last_import_time": universe_status.get("last_import_time"),
                "import_source": universe_status.get("import_source", "NOT_CONFIGURED"),
            },
            "brokers": broker_readiness,
            "market_data": {
                "market_data_mode": market_data_status.get("market_data_mode", "not_ready"),
                "primary_market_data_broker": market_data_status.get("primary_market_data_broker", self.settings.primary_market_data_broker),
                "standby_market_data_broker": market_data_status.get("standby_market_data_broker", self.settings.standby_market_data_broker),
                "active_market_data_source": market_data_status.get("active_market_data_source", "fixture"),
                "primary_connection_state": market_data_status.get("primary_connection_state", "NOT_READY"),
                "standby_connection_state": market_data_status.get("standby_connection_state", "NOT_READY"),
                "last_valid_tick": (market_data_status.get("heartbeat") or {}).get("last_valid_tick"),
                "quote_cache_size": market_data_status.get("quote_cache_size", 0),
                "active_subscriptions": market_data_status.get("active_subscriptions", 0),
                "stale_instruments": market_data_status.get("stale_instruments", 0),
                "reconnect_count": (market_data_status.get("heartbeat") or {}).get("reconnect_count", 0),
                "candle_builder_state": market_data_status.get("candle_builder_state", "NOT_READY"),
            },
        }
        self.state_store.set("health", payload)
        return payload
