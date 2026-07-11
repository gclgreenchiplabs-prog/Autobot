from __future__ import annotations

from typing import Any, Dict

from app.lifecycle import AppLifecycle
from app.state_store import StateStore


class ControlService:
    def __init__(self, state_store: StateStore | None = None) -> None:
        self.state_store = state_store or StateStore()
        self.lifecycle = AppLifecycle(state_store=self.state_store)

    def apply(self, action: str) -> Dict[str, Any]:
        if action == "start":
            return self.lifecycle.start()
        if action == "stop":
            return self.lifecycle.stop()
        if action == "pause":
            return self.lifecycle.pause()
        if action == "resume":
            return self.lifecycle.resume()
        if action == "scan":
            self.state_store.set("scan_requested", True)
            return {"status": "queued", "action": action}
        if action == "kill-switch":
            return self.lifecycle.trigger_kill_switch()
        raise ValueError(f"unsupported action: {action}")
