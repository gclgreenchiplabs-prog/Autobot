from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class PositionSnapshot:
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
    current_price: float
    highest_price: float
    highest_profit: float
    current_stop: Optional[float]
    initial_stop: Optional[float]
    t1: Optional[float]
    t2: Optional[float]
    t3: Optional[float]
    next_predicted_target: Optional[float]
    t1_status: str
    t2_status: str
    t3_status: str
    current_pnl: float
    current_pnl_pct: float
    locked_profit: float
    capital_used_trade: float
    hold_duration_seconds: int
    hold_reason: str
    exit_condition: str
    position_status: str
    timestamp_utc: str
    timestamp_ist: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
