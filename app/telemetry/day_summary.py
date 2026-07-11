from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class DaySummary:
    realized_pnl: float
    unrealized_pnl: float
    total_day_pnl: float
    capital_used_day: float
    capital_reserved: float
    capital_available: float
    account_equity: float
    wins: int
    losses: int
    open_trades: int
    closed_trades: int
    execution_mode: str
    configured_primary_broker: str
    active_execution_broker: str
    standby_broker: str
    timestamp_utc: str
    timestamp_ist: str
    summary_date_ist: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
