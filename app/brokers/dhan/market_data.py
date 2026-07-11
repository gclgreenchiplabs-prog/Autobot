from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.market_data.base import AdapterReadiness, AdapterState, DataState, MarketDataAdapter
from app.settings import Settings


class DhanMarketDataAdapter(MarketDataAdapter):
    source = "dhan"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._state = self._initial_state()

    def _initial_state(self) -> str:
        if not self.settings.dhan_market_data_enable:
            return AdapterState.NOT_CONFIGURED.value
        if not (self.settings.api_key and self.settings.access_token):
            return AdapterState.NOT_CONFIGURED.value
        return AdapterState.DISCONNECTED.value

    def connect(self) -> Dict[str, Any]:
        if self._state == AdapterState.NOT_CONFIGURED.value:
            return self.health_snapshot()
        self._state = AdapterState.FAILED.value
        return self.health_snapshot()

    def disconnect(self) -> Dict[str, Any]:
        if self._state != AdapterState.NOT_CONFIGURED.value:
            self._state = AdapterState.DISCONNECTED.value
        return self.health_snapshot()

    def reconnect(self) -> Dict[str, Any]:
        if self._state == AdapterState.NOT_CONFIGURED.value:
            return self.health_snapshot()
        self._state = AdapterState.RECONNECTING.value
        self._state = AdapterState.FAILED.value
        return self.health_snapshot()

    def is_connected(self) -> bool:
        return self._state == AdapterState.CONNECTED.value

    def readiness(self) -> Dict[str, Any]:
        return AdapterReadiness(
            state=self._state,
            ready=self.is_connected(),
            reason="credentials missing" if self._state == AdapterState.NOT_CONFIGURED.value else "live connection not attempted in this sprint",
            data_state=DataState.LIVE.value if self.is_connected() else DataState.NOT_READY.value,
        ).to_dict()

    def subscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        return {"subscribed": [item["instrument_id"] for item in instruments], "state": self._state}

    def unsubscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        return {"unsubscribed": [item["instrument_id"] for item in instruments], "state": self._state}

    def resubscribe_all(self) -> Dict[str, Any]:
        return {"resubscribed": [], "state": self._state}

    def get_quote(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_snapshot(self, instrument_ids: Iterable[str]) -> List[Dict[str, Any]]:
        return []

    def get_historical_candles(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def health_snapshot(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "connection_state": self._state,
            "data_state": DataState.LIVE.value if self.is_connected() else DataState.NOT_READY.value,
        }
