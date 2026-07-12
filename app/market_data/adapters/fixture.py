from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from app.market_data.base import AdapterReadiness, AdapterState, DataState, MarketDataAdapter


class FixtureMarketDataAdapter(MarketDataAdapter):
    source = "fixture"

    def __init__(self, *, timezone_name: str = "Asia/Kolkata", auto_start: bool = False) -> None:
        self.timezone_name = timezone_name
        self.auto_start = auto_start
        self._state = AdapterState.DISCONNECTED.value
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._latest: Dict[str, Dict[str, Any]] = {}
        self._scripted_ticks: Dict[str, List[Dict[str, Any]]] = {}
        self._pointer: Dict[str, int] = {}
        self._last_heartbeat: Optional[str] = None

    def connect(self) -> Dict[str, Any]:
        self._state = AdapterState.CONNECTED.value
        self._last_heartbeat = datetime.now(timezone.utc).isoformat()
        return self.health_snapshot()

    def disconnect(self) -> Dict[str, Any]:
        self._state = AdapterState.DISCONNECTED.value
        return self.health_snapshot()

    def reconnect(self) -> Dict[str, Any]:
        self._state = AdapterState.RECONNECTING.value
        self._last_heartbeat = datetime.now(timezone.utc).isoformat()
        self._state = AdapterState.CONNECTED.value
        return self.health_snapshot()

    def is_connected(self) -> bool:
        return self._state == AdapterState.CONNECTED.value

    def readiness(self) -> Dict[str, Any]:
        return AdapterReadiness(
            state=self._state,
            ready=self.is_connected(),
            reason="fixture adapter ready" if self.is_connected() else "fixture adapter disconnected",
            data_state=DataState.FIXTURE.value if self.is_connected() else DataState.NOT_READY.value,
        ).to_dict()

    def subscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        subscribed = []
        for instrument in instruments:
            instrument_id = instrument["instrument_id"]
            self._subscriptions[instrument_id] = dict(instrument)
            self._scripted_ticks[instrument_id] = self._build_script(instrument)
            self._pointer[instrument_id] = 0
            subscribed.append(instrument_id)
        return {"subscribed": subscribed, "state": self._state}

    def unsubscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        removed = []
        for instrument in instruments:
            instrument_id = instrument["instrument_id"]
            if instrument_id in self._subscriptions:
                removed.append(instrument_id)
                self._subscriptions.pop(instrument_id, None)
                self._scripted_ticks.pop(instrument_id, None)
                self._pointer.pop(instrument_id, None)
        return {"unsubscribed": removed, "state": self._state}

    def resubscribe_all(self) -> Dict[str, Any]:
        return {"resubscribed": list(self._subscriptions.keys()), "state": self._state}

    def get_quote(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        return dict(self._latest[instrument_id]) if instrument_id in self._latest else None

    def get_snapshot(self, instrument_ids: Iterable[str]) -> List[Dict[str, Any]]:
        return [dict(self._latest[item]) for item in instrument_ids if item in self._latest]

    def get_historical_candles(self, **kwargs: Any) -> List[Dict[str, Any]]:
        return []

    def health_snapshot(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "connection_state": self._state,
            "data_state": DataState.FIXTURE.value if self.is_connected() else DataState.NOT_READY.value,
            "subscription_count": len(self._subscriptions),
            "last_heartbeat": self._last_heartbeat,
        }

    def emit_next_ticks(self, count: int = 1) -> List[Dict[str, Any]]:
        emitted: List[Dict[str, Any]] = []
        for instrument_id in list(self._subscriptions.keys()):
            for _ in range(count):
                pointer = self._pointer.get(instrument_id, 0)
                script = self._scripted_ticks.get(instrument_id, [])
                if pointer >= len(script):
                    continue
                tick = dict(script[pointer])
                self._pointer[instrument_id] = pointer + 1
                self._latest[instrument_id] = tick
                self._last_heartbeat = datetime.now(timezone.utc).isoformat()
                emitted.append(tick)
        return emitted

    def _build_script(self, instrument: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_timestamp = datetime(2026, 7, 12, 9, 15, tzinfo=ZoneInfo(self.timezone_name)).astimezone(timezone.utc)
        base_ltp = float(instrument.get("ltp") or instrument.get("last_price") or 100.0)
        base_bid = float(instrument.get("bid") or max(base_ltp - 0.1, 0.0))
        base_ask = float(instrument.get("ask") or base_ltp + 0.1)
        volume = int(instrument.get("volume") or 1000)
        ticks = []
        for index, delta in enumerate([0.0, 0.4, 0.8, 1.1, 0.9, 1.4], start=1):
            timestamp_utc = (base_timestamp + timedelta(minutes=index - 1, seconds=1)).isoformat()
            payload = {
                "tick_id": hashlib.sha256(f"{instrument['instrument_id']}:{index}".encode("utf-8")).hexdigest()[:16],
                "instrument_id": instrument["instrument_id"],
                "company_id": instrument["company_id"],
                "exchange": instrument["exchange"],
                "segment": instrument["segment"],
                "symbol": instrument["symbol"],
                "source": self.source,
                "data_mode": DataState.FIXTURE.value,
                "timestamp_exchange": timestamp_utc,
                "timestamp_received": timestamp_utc,
                "timestamp_utc": timestamp_utc,
                "timestamp_ist": datetime.fromisoformat(timestamp_utc).astimezone(ZoneInfo(self.timezone_name)).isoformat(),
                "sequence_number": index,
                "ltp": round(base_ltp + delta, 2),
                "last_quantity": 10,
                "open": base_ltp,
                "high": round(base_ltp + max(delta, 0), 2),
                "low": round(base_ltp - 0.3, 2),
                "previous_close": round(base_ltp - 0.2, 2),
                "bid": round(base_bid + delta, 2),
                "ask": round(base_ask + delta, 2),
                "bid_quantity": 100 + index,
                "ask_quantity": 120 + index,
                "volume": volume + index * 100,
                "traded_value": round((volume + index * 100) * (base_ltp + delta), 2),
                "vwap": round(base_ltp + delta / 2, 2),
                "open_interest": 1000 + index * 5,
                "change_in_oi": index * 5,
                "upper_circuit": round(base_ltp * 1.2, 2),
                "lower_circuit": round(base_ltp * 0.8, 2),
                "market_status": "OPEN",
                "raw_reference": {"fixture": True, "script_index": index},
            }
            ticks.append(payload)
        return ticks
