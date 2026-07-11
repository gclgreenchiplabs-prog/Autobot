from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

from app.database.repository import Repository
from app.event_bus import EventBus
from app.settings import Settings
from app.state_store import StateStore
from app.telemetry.account_snapshot import AccountSnapshot
from app.telemetry.day_summary import DaySummary
from app.telemetry.position_snapshot import PositionSnapshot
from app.telemetry.trade_snapshot import TradeSnapshot


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _side_multiplier(side: Any) -> int:
    normalized = str(side or "BUY").strip().upper()
    if normalized in {"SELL", "SHORT"}:
        return -1
    return 1


class TelemetryService:
    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        repository: Repository,
        event_bus: EventBus,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.repository = repository
        self.event_bus = event_bus
        self._ist_zone = ZoneInfo(self.settings.timezone)

    def _now(self) -> tuple[datetime, datetime]:
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(self._ist_zone)
        return now_utc, now_ist

    def _execution_context(self) -> Dict[str, str]:
        if self.settings.is_paper_mode:
            return {
                "execution_mode": "paper",
                "configured_primary_broker": "fyers",
                "active_execution_broker": "paper",
                "standby_broker": "dhan",
            }
        return {
            "execution_mode": self.settings.trading_mode,
            "configured_primary_broker": self.settings.primary_broker,
            "active_execution_broker": self.settings.primary_broker,
            "standby_broker": self.settings.standby_broker,
        }

    def _account_state(self) -> Dict[str, Any]:
        return dict(self.state_store.get("account") or {"opening_capital": self.settings.opening_capital, "capital_reserved": 0.0})

    def _positions_state(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.state_store.get("positions", [])]

    def _closed_trades_state(self) -> List[Dict[str, Any]]:
        return [dict(item) for item in self.state_store.get("closed_trades", [])]

    def _position_capital_used(self, position: Dict[str, Any]) -> float:
        explicit = position.get("capital_used_trade")
        if explicit is not None:
            return round(_as_float(explicit), 2)
        return round(_as_float(position.get("entry_price")) * max(_as_int(position.get("quantity"), 0), 0), 2)

    def _position_current_pnl(self, position: Dict[str, Any]) -> float:
        explicit = position.get("current_pnl")
        if explicit is not None:
            return round(_as_float(explicit), 2)
        entry_price = _as_float(position.get("entry_price"))
        current_price = _as_float(position.get("current_price"), entry_price)
        quantity = _as_int(position.get("quantity"), 0)
        return round((current_price - entry_price) * quantity * _side_multiplier(position.get("side")), 2)

    def _position_locked_profit(self, position: Dict[str, Any]) -> float:
        explicit = position.get("locked_profit")
        if explicit is not None:
            return round(_as_float(explicit), 2)
        entry_price = _as_float(position.get("entry_price"))
        current_stop = _as_float(position.get("current_stop"), _as_float(position.get("initial_stop")))
        quantity = _as_int(position.get("quantity"), 0)
        locked = max((current_stop - entry_price) * quantity * _side_multiplier(position.get("side")), 0.0)
        return round(locked, 2)

    def build_account_snapshot(self, reason: str = "runtime") -> AccountSnapshot:
        now_utc, now_ist = self._now()
        execution_context = self._execution_context()
        positions = self._positions_state()
        closed_trades = self._closed_trades_state()
        account_state = self._account_state()

        opening_capital = _as_float(account_state.get("opening_capital"), self.settings.opening_capital)
        capital_reserved = _as_float(account_state.get("capital_reserved"))
        capital_used_day = round(sum(self._position_capital_used(position) for position in positions), 2)
        realized_pnl = round(sum(_as_float(trade.get("net_pnl", trade.get("trade_pnl", 0.0))) for trade in closed_trades), 2)
        unrealized_pnl = round(sum(self._position_current_pnl(position) for position in positions), 2)
        total_day_pnl = round(realized_pnl + unrealized_pnl, 2)
        account_equity = round(opening_capital + total_day_pnl, 2)
        capital_available = round(opening_capital - capital_used_day - capital_reserved + total_day_pnl, 2)
        wins = sum(1 for trade in closed_trades if _as_float(trade.get("net_pnl", trade.get("trade_pnl", 0.0))) > 0)
        losses = sum(1 for trade in closed_trades if _as_float(trade.get("net_pnl", trade.get("trade_pnl", 0.0))) < 0)

        return AccountSnapshot(
            opening_capital=round(opening_capital, 2),
            account_equity=account_equity,
            capital_used_day=capital_used_day,
            capital_reserved=round(capital_reserved, 2),
            capital_available=capital_available,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_day_pnl=total_day_pnl,
            wins=wins,
            losses=losses,
            open_trades=len(positions),
            closed_trades=len(closed_trades),
            execution_mode=execution_context["execution_mode"],
            configured_primary_broker=execution_context["configured_primary_broker"],
            active_execution_broker=execution_context["active_execution_broker"],
            standby_broker=execution_context["standby_broker"],
            timestamp_utc=now_utc.isoformat(),
            timestamp_ist=now_ist.isoformat(),
            snapshot_reason=reason,
        )

    def build_position_snapshots(self) -> List[PositionSnapshot]:
        now_utc, now_ist = self._now()
        snapshots: List[PositionSnapshot] = []
        for raw_position in self._positions_state():
            entry_price = _as_float(raw_position.get("entry_price"))
            current_price = _as_float(raw_position.get("current_price"), entry_price)
            capital_used_trade = self._position_capital_used(raw_position)
            current_pnl = self._position_current_pnl(raw_position)
            current_pnl_pct = round((current_pnl / capital_used_trade) * 100, 2) if capital_used_trade else 0.0
            highest_price = _as_float(raw_position.get("highest_price"), current_price)
            highest_profit = round(_as_float(raw_position.get("highest_profit"), current_pnl), 2)
            hold_started = _parse_timestamp(raw_position.get("entry_timestamp"))
            hold_duration_seconds = int((now_utc - hold_started.astimezone(timezone.utc)).total_seconds()) if hold_started else 0

            snapshots.append(
                PositionSnapshot(
                    trade_id=str(raw_position.get("trade_id") or raw_position.get("symbol") or "trade"),
                    symbol=str(raw_position.get("symbol") or ""),
                    underlying=raw_position.get("underlying"),
                    exchange=raw_position.get("exchange"),
                    instrument_type=raw_position.get("instrument_type"),
                    option_type=raw_position.get("option_type"),
                    strike=raw_position.get("strike"),
                    expiry=raw_position.get("expiry"),
                    side=raw_position.get("side"),
                    quantity=_as_int(raw_position.get("quantity"), 0),
                    lots=max(_as_int(raw_position.get("lots"), 1), 1),
                    entry_price=round(entry_price, 2),
                    current_price=round(current_price, 2),
                    highest_price=round(highest_price, 2),
                    highest_profit=highest_profit,
                    current_stop=raw_position.get("current_stop"),
                    initial_stop=raw_position.get("initial_stop"),
                    t1=raw_position.get("t1"),
                    t2=raw_position.get("t2"),
                    t3=raw_position.get("t3"),
                    next_predicted_target=raw_position.get("next_predicted_target"),
                    t1_status=str(raw_position.get("t1_status") or "PENDING"),
                    t2_status=str(raw_position.get("t2_status") or "PENDING"),
                    t3_status=str(raw_position.get("t3_status") or "PENDING"),
                    current_pnl=current_pnl,
                    current_pnl_pct=current_pnl_pct,
                    locked_profit=self._position_locked_profit(raw_position),
                    capital_used_trade=capital_used_trade,
                    hold_duration_seconds=max(hold_duration_seconds, 0),
                    hold_reason=str(raw_position.get("hold_reason") or "Position remains active."),
                    exit_condition=str(raw_position.get("exit_condition") or "Trailing-stop or strategy invalidation."),
                    position_status=str(raw_position.get("position_status") or "OPEN"),
                    timestamp_utc=now_utc.isoformat(),
                    timestamp_ist=now_ist.isoformat(),
                )
            )
        return snapshots

    def build_trade_snapshots(self) -> List[TradeSnapshot]:
        now_utc, now_ist = self._now()
        snapshots: List[TradeSnapshot] = []
        raw_positions = self._positions_state()
        position_snapshots = self.build_position_snapshots()
        position_by_trade = {str(item.get("trade_id") or item.get("symbol") or "trade"): item for item in raw_positions}

        for position in position_snapshots:
            raw_position = position_by_trade.get(position.trade_id, {})
            snapshots.append(
                TradeSnapshot(
                    trade_id=position.trade_id,
                    symbol=position.symbol,
                    underlying=position.underlying,
                    exchange=position.exchange,
                    instrument_type=position.instrument_type,
                    option_type=position.option_type,
                    strike=position.strike,
                    expiry=position.expiry,
                    side=position.side,
                    quantity=position.quantity,
                    lots=position.lots,
                    entry_price=position.entry_price,
                    exit_price=None,
                    current_price=position.current_price,
                    capital_used_trade=position.capital_used_trade,
                    capital_released=0.0,
                    realized_pnl=0.0,
                    unrealized_pnl=position.current_pnl,
                    total_pnl=position.current_pnl,
                    highest_price=position.highest_price,
                    highest_profit=position.highest_profit,
                    mfe=position.highest_profit,
                    mae=None,
                    entry_timestamp=raw_position.get("entry_timestamp"),
                    exit_timestamp=None,
                    hold_duration_seconds=position.hold_duration_seconds,
                    exit_reason=None,
                    status=position.position_status,
                    timestamp_utc=now_utc.isoformat(),
                    timestamp_ist=now_ist.isoformat(),
                )
            )

        for trade in self._closed_trades_state():
            entry_timestamp = _parse_timestamp(trade.get("entry_timestamp"))
            exit_timestamp = _parse_timestamp(trade.get("exit_timestamp"))
            hold_duration_seconds = 0
            if entry_timestamp and exit_timestamp:
                hold_duration_seconds = int((exit_timestamp.astimezone(timezone.utc) - entry_timestamp.astimezone(timezone.utc)).total_seconds())
            realized_pnl = round(_as_float(trade.get("net_pnl", trade.get("trade_pnl", 0.0))), 2)
            snapshots.append(
                TradeSnapshot(
                    trade_id=str(trade.get("trade_id") or trade.get("symbol") or "closed-trade"),
                    symbol=str(trade.get("symbol") or ""),
                    underlying=trade.get("underlying"),
                    exchange=trade.get("exchange"),
                    instrument_type=trade.get("instrument_type"),
                    option_type=trade.get("option_type"),
                    strike=trade.get("strike"),
                    expiry=trade.get("expiry"),
                    side=trade.get("side"),
                    quantity=_as_int(trade.get("quantity"), 0),
                    lots=max(_as_int(trade.get("lots"), 1), 1),
                    entry_price=round(_as_float(trade.get("entry_price")), 2),
                    exit_price=round(_as_float(trade.get("exit_price")), 2),
                    current_price=None,
                    capital_used_trade=round(_as_float(trade.get("capital_used_trade")), 2),
                    capital_released=round(_as_float(trade.get("capital_released")), 2),
                    realized_pnl=realized_pnl,
                    unrealized_pnl=0.0,
                    total_pnl=realized_pnl,
                    highest_price=trade.get("highest_price"),
                    highest_profit=trade.get("highest_profit"),
                    mfe=trade.get("mfe"),
                    mae=trade.get("mae"),
                    entry_timestamp=trade.get("entry_timestamp"),
                    exit_timestamp=trade.get("exit_timestamp"),
                    hold_duration_seconds=max(hold_duration_seconds, 0),
                    exit_reason=trade.get("exit_reason"),
                    status=str(trade.get("status") or "CLOSED"),
                    timestamp_utc=now_utc.isoformat(),
                    timestamp_ist=now_ist.isoformat(),
                )
            )

        return snapshots

    def build_day_summary(self) -> DaySummary:
        account = self.build_account_snapshot(reason="day-summary")
        now_utc, now_ist = self._now()
        return DaySummary(
            realized_pnl=account.realized_pnl,
            unrealized_pnl=account.unrealized_pnl,
            total_day_pnl=account.total_day_pnl,
            capital_used_day=account.capital_used_day,
            capital_reserved=account.capital_reserved,
            capital_available=account.capital_available,
            account_equity=account.account_equity,
            wins=account.wins,
            losses=account.losses,
            open_trades=account.open_trades,
            closed_trades=account.closed_trades,
            execution_mode=account.execution_mode,
            configured_primary_broker=account.configured_primary_broker,
            active_execution_broker=account.active_execution_broker,
            standby_broker=account.standby_broker,
            timestamp_utc=now_utc.isoformat(),
            timestamp_ist=now_ist.isoformat(),
            summary_date_ist=now_ist.date().isoformat(),
        )

    def recent_closed_trades(self, window_minutes: int) -> List[TradeSnapshot]:
        threshold_utc = datetime.now(timezone.utc).timestamp() - max(window_minutes, 0) * 60
        items: List[TradeSnapshot] = []
        for snapshot in self.build_trade_snapshots():
            if snapshot.status not in {"CLOSED", "EXITED"}:
                continue
            exit_timestamp = _parse_timestamp(snapshot.exit_timestamp)
            if exit_timestamp is None:
                continue
            if exit_timestamp.astimezone(timezone.utc).timestamp() >= threshold_utc:
                items.append(snapshot)
        return items

    def persist_snapshots(self, reason: str = "runtime") -> Dict[str, Any]:
        account = self.build_account_snapshot(reason=reason)
        positions = self.build_position_snapshots()
        trades = self.build_trade_snapshots()
        day_summary = self.build_day_summary()

        self.repository.save_account_snapshot(account.to_dict())
        for position in positions:
            self.repository.save_position_snapshot(position.to_dict())
        for trade in trades:
            self.repository.save_trade_snapshot(trade.to_dict())
        self.repository.save_day_summary(day_summary.to_dict())

        return {
            "account": account.to_dict(),
            "positions": [position.to_dict() for position in positions],
            "trades": [trade.to_dict() for trade in trades],
            "day_summary": day_summary.to_dict(),
        }


__all__ = [
    "AccountSnapshot",
    "DaySummary",
    "PositionSnapshot",
    "TelemetryService",
    "TradeSnapshot",
]
