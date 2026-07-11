from __future__ import annotations

from typing import Any, Dict, List


class ReconciliationState:
    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    def mark_timeout(self, reason: str = "timeout") -> Dict[str, Any]:
        payload = {"status": "BROKER_RECONCILIATION", "reason": reason}
        self._events.append(payload)
        return payload

    def as_dict(self) -> Dict[str, Any]:
        return {"status": "BROKER_RECONCILIATION" if self._events else "OK", "events": list(self._events)}
