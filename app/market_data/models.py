from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class MarketQuoteSnapshot:
    instrument_id: str
    source: str
    timestamp_utc: str
    timestamp_ist: str
    ltp: float
    open: float
    high: float
    low: float
    previous_close: float
    bid: float
    ask: float
    bid_quantity: int
    ask_quantity: int
    volume: int
    traded_value: float
    vwap: float
    open_interest: float
    change_in_oi: float
    data_mode: str
    sequence_number: int
    received_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LiquiditySnapshot:
    instrument_id: str
    liquidity_score: int
    liquidity_class: str
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualitySnapshot:
    instrument_id: str
    quality_score: int
    quality_class: str
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
