from __future__ import annotations

from typing import Any, Dict

from app.state_store import StateStore


class DashboardService:
    def __init__(self, state_store: StateStore | None = None) -> None:
        self.state_store = state_store or StateStore()

    def get_state(self) -> Dict[str, Any]:
        return {
            "lifecycle": self.state_store.get("lifecycle") or {"status": "initialized", "mode": "paper", "kill_switch": False},
            "orders": self.state_store.get("orders", []),
            "positions": self.state_store.get("positions", []),
        }
