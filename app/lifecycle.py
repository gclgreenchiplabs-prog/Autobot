from __future__ import annotations

from typing import Any, Dict, Optional

from app.state_store import StateStore


class AppLifecycle:
    def __init__(self, state_store: Optional[StateStore] = None, mode: Optional[str] = None) -> None:
        self.state_store = state_store or StateStore()
        self.mode = mode or "paper"
        self.status = "initialized"
        self.kill_switch = False

    def _persist(self) -> Dict[str, Any]:
        payload = {"status": self.status, "mode": self.mode, "kill_switch": self.kill_switch}
        self.state_store.set("lifecycle", payload)
        return payload

    def start(self) -> Dict[str, Any]:
        self.status = "running"
        self.kill_switch = False
        return self._persist()

    def stop(self) -> Dict[str, Any]:
        self.status = "stopped"
        self.kill_switch = False
        return self._persist()

    def pause(self) -> Dict[str, Any]:
        self.status = "paused"
        return self._persist()

    def resume(self) -> Dict[str, Any]:
        self.status = "running"
        return self._persist()

    def trigger_kill_switch(self) -> Dict[str, Any]:
        self.kill_switch = True
        self.status = "stopped"
        return self._persist()
