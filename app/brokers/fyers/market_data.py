from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from app.brokers.readiness import BrokerCapabilityEvaluator
from app.market_data.base import AdapterState, DataState, MarketDataAdapter
from app.settings import Settings

try:
    import fyers_apiv3  # type: ignore # noqa: F401

    FYERS_SDK_AVAILABLE = True
except Exception:
    FYERS_SDK_AVAILABLE = False


class FyersMarketDataAdapter(MarketDataAdapter):
    source = "fyers"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._state = self._initial_state()

    def _initial_state(self) -> str:
        if not self.settings.fyers_configured:
            return "NOT_CONFIGURED"
        if self.settings.market_data_mode != "LIVE" or not self.settings.live_market_data_enable or not self.settings.fyers_market_data_enable:
            return "DISABLED"
        if not FYERS_SDK_AVAILABLE:
            return "SDK_NOT_INSTALLED"
        if not (self.settings.fyers_client_id and self.settings.fyers_secret_key and self.settings.fyers_access_token):
            return "CREDENTIALS_MISSING"
        return AdapterState.DISCONNECTED.value

    def connect(self) -> Dict[str, Any]:
        if self._state in {"NOT_CONFIGURED", "DISABLED", "SDK_NOT_INSTALLED", "CREDENTIALS_MISSING"}:
            return self.health_snapshot()
        self._state = AdapterState.FAILED.value
        return self.health_snapshot()

    def disconnect(self) -> Dict[str, Any]:
        if self._state not in {"NOT_CONFIGURED", "DISABLED", "SDK_NOT_INSTALLED", "CREDENTIALS_MISSING"}:
            self._state = AdapterState.DISCONNECTED.value
        return self.health_snapshot()

    def reconnect(self) -> Dict[str, Any]:
        if self._state in {"NOT_CONFIGURED", "DISABLED", "SDK_NOT_INSTALLED", "CREDENTIALS_MISSING"}:
            return self.health_snapshot()
        self._state = AdapterState.RECONNECTING.value
        self._state = AdapterState.FAILED.value
        return self.health_snapshot()

    def is_connected(self) -> bool:
        return self._state == AdapterState.CONNECTED.value

    def readiness(self) -> Dict[str, Any]:
        capability = self.market_data_readiness()
        state = capability["status"]
        return {
            **capability,
            "state": state,
            "ready": capability["market_data_ready"],
            "data_state": DataState.LIVE.value if capability["connected"] else DataState.NOT_READY.value,
        }

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
        readiness = self.readiness()
        return {
            "source": self.source,
            "connection_state": readiness["state"],
            "data_state": readiness["data_state"],
            "sdk_available": FYERS_SDK_AVAILABLE,
            "configured": readiness["configured"],
            "enabled": readiness["enabled"],
            "credentials_present": readiness["credentials_present"],
            "authenticated": readiness["authenticated"],
            "connected": readiness["connected"],
            "market_data_ready": readiness["market_data_ready"],
            "active": readiness["active"],
            "reason": readiness["reason"],
            "last_error": readiness["last_error"],
            "last_checked_at": readiness["last_checked_at"],
        }

    def configuration_readiness(self) -> Dict[str, Any]:
        return self._evaluator().configuration_readiness().to_dict()

    def authentication_readiness(self) -> Dict[str, Any]:
        return self._evaluator().authentication_readiness().to_dict()

    def market_data_readiness(self) -> Dict[str, Any]:
        return self._evaluator().market_data_readiness().to_dict()

    def option_chain_readiness(self) -> Dict[str, Any]:
        return self._evaluator().option_chain_readiness().to_dict()

    def execution_readiness(self) -> Dict[str, Any]:
        return self._evaluator().execution_readiness().to_dict()

    def _evaluator(self) -> BrokerCapabilityEvaluator:
        market_data_state = {
            "active_market_data_source": self.source if self.settings.market_data_mode == "LIVE" else "fixture",
        }
        return BrokerCapabilityEvaluator(
            settings=self.settings,
            broker=self.source,
            sdk_available=FYERS_SDK_AVAILABLE,
            authenticated=False,
            connected=self.is_connected(),
            market_data_state=market_data_state,
            market_data_capability_state={"state": self._state, "reason": self._state.replace("_", " ").title(), "connected": self.is_connected(), "market_data_ready": False},
        )
