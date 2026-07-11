from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from app.scheduler.market_clock import MarketClock
from app.state_store import StateStore


class SessionScheduler:
    def __init__(self, market_clock: MarketClock, state_store: StateStore) -> None:
        self.market_clock = market_clock
        self.state_store = state_store
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def get_state(self) -> Dict[str, Any]:
        current = self.market_clock.current_ist()
        state = self.market_clock.current_session_state(current)
        payload = {
            "session_state": state,
            "ist_time": current.isoformat(),
            "running": self._running,
            "holiday_calendar_state": "NOT_CONFIGURED",
        }
        self.state_store.set("session", payload)
        return payload
