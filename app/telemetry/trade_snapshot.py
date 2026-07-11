from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class TradeSnapshot:
    trade_id: str
    symbol: str
    underlying: Optional[str]
    exchange: Optional[str]
    instrument_type: Optional[str]
    option_type: Optional[str]
    strike: Optional[float]
    expiry: Optional[str]
    side: Optional[str]
    quantity: int
    lots: int
    entry_price: float
    exit_price: Optional[float]
    current_price: Optional[float]
    capital_used_trade: float
    capital_released: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    highest_price: Optional[float]
    highest_profit: Optional[float]
    mfe: Optional[float]
    mae: Optional[float]
    entry_timestamp: Optional[str]
    exit_timestamp: Optional[str]
    hold_duration_seconds: int
    exit_reason: Optional[str]
    status: str
    timestamp_utc: str
    timestamp_ist: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
