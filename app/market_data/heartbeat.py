from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.settings import Settings


class HeartbeatMonitor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.last_socket_message: Optional[str] = None
        self.last_valid_tick: Optional[str] = None
        self.last_heartbeat: Optional[str] = None
        self.last_reconnect: Optional[str] = None
        self.reconnect_count = 0

    def record_socket_message(self, timestamp: Optional[str] = None) -> None:
        self.last_socket_message = timestamp or datetime.now(timezone.utc).isoformat()
        self.last_heartbeat = self.last_socket_message

    def record_valid_tick(self, timestamp: str) -> None:
        self.last_valid_tick = timestamp
        self.last_heartbeat = datetime.now(timezone.utc).isoformat()

    def record_reconnect(self) -> None:
        self.last_reconnect = datetime.now(timezone.utc).isoformat()
        self.reconnect_count += 1

    def state(self, *, active_subscription_count: int, stale_instrument_count: int) -> str:
        if self.last_valid_tick is None and active_subscription_count == 0:
            return "NOT_READY"
        now = datetime.now(timezone.utc)
        last_reference = self.last_valid_tick or self.last_socket_message
        if last_reference is None:
            return "NOT_READY"
        age = (now - datetime.fromisoformat(last_reference.replace("Z", "+00:00")).astimezone(timezone.utc)).total_seconds()
        if age >= self.settings.market_data_failed_seconds:
            return "FAILED"
        if age >= self.settings.market_data_stale_seconds or stale_instrument_count > 0:
            return "STALE"
        if age >= self.settings.market_data_heartbeat_seconds:
            return "DEGRADED"
        return "HEALTHY"

    def snapshot(self, *, active_subscription_count: int, stale_instrument_count: int, quote_cache_size: int) -> Dict[str, Any]:
        return {
            "state": self.state(
                active_subscription_count=active_subscription_count,
                stale_instrument_count=stale_instrument_count,
            ),
            "last_socket_message": self.last_socket_message,
            "last_valid_tick": self.last_valid_tick,
            "last_heartbeat": self.last_heartbeat,
            "last_reconnect": self.last_reconnect,
            "reconnect_count": self.reconnect_count,
            "stale_instrument_count": stale_instrument_count,
            "active_subscription_count": active_subscription_count,
            "quote_cache_size": quote_cache_size,
        }
