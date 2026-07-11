from __future__ import annotations

from typing import Any, Dict, List


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._order: List[str] = []

    def register(self, name: str, service: Any) -> None:
        if name in self._services:
            raise ValueError(f"Duplicate service name: {name}")
        self._services[name] = service
        self._order.append(name)

    def get(self, name: str) -> Any:
        return self._services[name]

    def list(self) -> List[Dict[str, Any]]:
        return [{"name": name, "ready": True} for name in self._order]
