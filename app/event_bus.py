from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any, Deque, Dict, List


class EventBus:
    def __init__(self, max_events: int = 100) -> None:
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)
        self._lock = Lock()

    def publish(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._events.append(event)
            return event

    def list_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)
