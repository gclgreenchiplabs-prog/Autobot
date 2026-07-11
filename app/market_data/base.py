from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo


class AdapterState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    FAILED = "FAILED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    SDK_NOT_INSTALLED = "SDK_NOT_INSTALLED"


class DataState(str, Enum):
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    HISTORICAL = "HISTORICAL"
    FIXTURE = "FIXTURE"
    STALE = "STALE"
    NOT_READY = "NOT_READY"


@dataclass
class AdapterReadiness:
    state: str
    ready: bool
    reason: str = ""
    data_state: str = DataState.NOT_READY.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedTick:
    tick_id: str
    instrument_id: str
    company_id: str
    exchange: str
    segment: str
    symbol: str
    source: str
    data_mode: str
    timestamp_exchange: str
    timestamp_received: str
    timestamp_utc: str
    timestamp_ist: str
    sequence_number: Optional[int] = None
    ltp: Optional[float] = None
    last_quantity: Optional[int] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_quantity: Optional[int] = None
    ask_quantity: Optional[int] = None
    volume: Optional[int] = None
    traded_value: Optional[float] = None
    vwap: Optional[float] = None
    open_interest: Optional[float] = None
    change_in_oi: Optional[float] = None
    upper_circuit: Optional[float] = None
    lower_circuit: Optional[float] = None
    market_status: Optional[str] = None
    raw_reference: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, *, timezone_name: str = "Asia/Kolkata", **payload: Any) -> "NormalizedTick":
        now_utc = datetime.now(timezone.utc)
        timestamp_utc = str(payload.get("timestamp_utc") or now_utc.isoformat())
        base_dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        return cls(
            tick_id=str(payload["tick_id"]),
            instrument_id=str(payload["instrument_id"]),
            company_id=str(payload["company_id"]),
            exchange=str(payload["exchange"]),
            segment=str(payload["segment"]),
            symbol=str(payload["symbol"]),
            source=str(payload["source"]).lower(),
            data_mode=str(payload["data_mode"]).upper(),
            timestamp_exchange=str(payload.get("timestamp_exchange") or timestamp_utc),
            timestamp_received=str(payload.get("timestamp_received") or now_utc.isoformat()),
            timestamp_utc=base_dt.isoformat(),
            timestamp_ist=base_dt.astimezone(ZoneInfo(timezone_name)).isoformat(),
            sequence_number=payload.get("sequence_number"),
            ltp=payload.get("ltp"),
            last_quantity=payload.get("last_quantity"),
            open=payload.get("open"),
            high=payload.get("high"),
            low=payload.get("low"),
            previous_close=payload.get("previous_close"),
            bid=payload.get("bid"),
            ask=payload.get("ask"),
            bid_quantity=payload.get("bid_quantity"),
            ask_quantity=payload.get("ask_quantity"),
            volume=payload.get("volume"),
            traded_value=payload.get("traded_value"),
            vwap=payload.get("vwap"),
            open_interest=payload.get("open_interest"),
            change_in_oi=payload.get("change_in_oi"),
            upper_circuit=payload.get("upper_circuit"),
            lower_circuit=payload.get("lower_circuit"),
            market_status=payload.get("market_status"),
            raw_reference=dict(payload.get("raw_reference") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketDataAdapter(ABC):
    source: str

    @abstractmethod
    def connect(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def reconnect(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def readiness(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def unsubscribe(self, instruments: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def resubscribe_all(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_snapshot(self, instrument_ids: Iterable[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_historical_candles(self, **kwargs: Any) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def health_snapshot(self) -> Dict[str, Any]:
        raise NotImplementedError
