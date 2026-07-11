from __future__ import annotations

from typing import Any, Dict, Optional

from app.state_store import StateStore


class AppLifecycle:
    def __init__(self, state_store: Optional[StateStore] = None, mode: Optional[str] = None) -> None:
        self.state_store = state_store or StateStore()
        self.mode = mode or "paper"
        self.status = "initialized"

    def start(self) -> Dict[str, Any]:
        self.status = "running"
        self.state_store.set("lifecycle", {"status": self.status, "mode": self.mode})
        return self.state_store.get("lifecycle")

    def stop(self) -> Dict[str, Any]:
        self.status = "stopped"
        self.state_store.set("lifecycle", {"status": self.status, "mode": self.mode})
        return self.state_store.get("lifecycle")
