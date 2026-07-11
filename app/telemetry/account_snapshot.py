from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class AccountSnapshot:
    opening_capital: float
    account_equity: float
    capital_used_day: float
    capital_reserved: float
    capital_available: float
    realized_pnl: float
    unrealized_pnl: float
    total_day_pnl: float
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
    snapshot_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
