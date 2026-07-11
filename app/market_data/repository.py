from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.instruments.repository import InstrumentRepository


class MarketDataRepository:
    def __init__(self, instrument_repository: InstrumentRepository) -> None:
        self.instrument_repository = instrument_repository

    def list_quality(self, *, quality_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_quality(quality_class=quality_class, limit=limit, offset=offset)

    def list_liquidity(self, *, liquidity_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_liquidity(liquidity_class=liquidity_class, limit=limit, offset=offset)

    def list_staleness(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_staleness(limit=limit, offset=offset)
