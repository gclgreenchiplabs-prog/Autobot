from __future__ import annotations

from typing import Any, Dict

from app.instruments.repository import InstrumentRepository


class InstrumentCache:
    def __init__(self, repository: InstrumentRepository) -> None:
        self.repository = repository

    def replace_snapshot(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.atomic_replace(bundle)
