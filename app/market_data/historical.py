from __future__ import annotations

from typing import Any, Dict, List

from app.market_data.repository import MarketDataRepository


class HistoricalDataService:
    def __init__(self, repository: MarketDataRepository) -> None:
        self.repository = repository

    def get_candles(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.repository.list_candles(**filters)
