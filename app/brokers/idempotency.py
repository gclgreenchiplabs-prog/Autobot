from __future__ import annotations

from typing import Any, Dict, Optional


class IdempotencyStore:
    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}

    def save(self, key: str, result: Dict[str, Any]) -> Dict[str, Any]:
        self._records[key] = {"key": key, "result": result}
        return self._records[key]

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._records.get(key)

    def clear(self) -> None:
        self._records.clear()
