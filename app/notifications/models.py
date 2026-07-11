from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


class NotificationType(str, Enum):
    BOT_STARTED = "BOT_STARTED"
    BOT_STOPPED = "BOT_STOPPED"
    BOT_PAUSED = "BOT_PAUSED"
    BOT_RESUMED = "BOT_RESUMED"
    BOT_HEARTBEAT = "BOT_HEARTBEAT"
    BROKER_CONNECTED = "BROKER_CONNECTED"
    BROKER_DISCONNECTED = "BROKER_DISCONNECTED"
    BROKER_DEGRADED = "BROKER_DEGRADED"
    BROKER_RECONCILIATION = "BROKER_RECONCILIATION"
    DATA_FEED_CONNECTED = "DATA_FEED_CONNECTED"
    DATA_FEED_STALE = "DATA_FEED_STALE"
    DATA_FEED_FAILED = "DATA_FEED_FAILED"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SIGNAL_REJECTED = "SIGNAL_REJECTED"
    SIGNAL_CHANGED = "SIGNAL_CHANGED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_ACKNOWLEDGED = "ORDER_ACKNOWLEDGED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_MODIFIED = "ORDER_MODIFIED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_UPDATED = "POSITION_UPDATED"
    POSITION_HOLD = "POSITION_HOLD"
    POSITION_T1_HIT = "POSITION_T1_HIT"
    POSITION_T2_HIT = "POSITION_T2_HIT"
    POSITION_T3_HIT = "POSITION_T3_HIT"
    POSITION_TSL_UPDATED = "POSITION_TSL_UPDATED"
    POSITION_PARTIAL_EXIT = "POSITION_PARTIAL_EXIT"
    POSITION_EXITED = "POSITION_EXITED"
    CAPITAL_UPDATED = "CAPITAL_UPDATED"
    RISK_BLOCKED = "RISK_BLOCKED"
    DAILY_LOSS_GUARD = "DAILY_LOSS_GUARD"
    PROFIT_LOCK_UPDATED = "PROFIT_LOCK_UPDATED"
    KILL_SWITCH_TRIGGERED = "KILL_SWITCH_TRIGGERED"
    MARKET_EVENT_DETECTED = "MARKET_EVENT_DETECTED"
    CORPORATE_EVENT_DETECTED = "CORPORATE_EVENT_DETECTED"
    NEWS_EVENT_DETECTED = "NEWS_EVENT_DETECTED"
    VOLATILITY_EVENT_DETECTED = "VOLATILITY_EVENT_DETECTED"
    LIQUIDITY_EVENT_DETECTED = "LIQUIDITY_EVENT_DETECTED"
    WATCHLIST_ADDED = "WATCHLIST_ADDED"
    WATCHLIST_REMOVED = "WATCHLIST_REMOVED"
    WATCHLIST_CHANGED = "WATCHLIST_CHANGED"
    FIVE_MINUTE_STATUS = "FIVE_MINUTE_STATUS"
    MARKET_CLOSE_SUMMARY = "MARKET_CLOSE_SUMMARY"
    DAILY_REVIEW_READY = "DAILY_REVIEW_READY"


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class NotificationRecord:
    notification_id: str
    notification_type: str
    severity: str
    timestamp_utc: str
    timestamp_ist: str
    correlation_id: Optional[str] = None
    trade_id: Optional[str] = None
    order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    strategy: Optional[str] = None
    symbol: Optional[str] = None
    underlying: Optional[str] = None
    exchange: Optional[str] = None
    instrument_type: Optional[str] = None
    option_type: Optional[str] = None
    strike: Optional[float] = None
    expiry: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[int] = None
    lots: Optional[int] = None
    title: str = ""
    summary: str = ""
    reason: Optional[str] = None
    event_source: Optional[str] = None
    entry_price: Optional[float] = None
    current_price: Optional[float] = None
    exit_price: Optional[float] = None
    initial_stop: Optional[float] = None
    current_stop: Optional[float] = None
    t1: Optional[float] = None
    t2: Optional[float] = None
    t3: Optional[float] = None
    stretch_target: Optional[float] = None
    next_predicted_target: Optional[float] = None
    t1_status: Optional[str] = None
    t2_status: Optional[str] = None
    t3_status: Optional[str] = None
    highest_price: Optional[float] = None
    highest_profit: Optional[float] = None
    locked_profit: Optional[float] = None
    mfe: Optional[float] = None
    mae: Optional[float] = None
    hold_duration_seconds: Optional[int] = None
    trade_pnl: Optional[float] = None
    trade_pnl_pct: Optional[float] = None
    day_realized_pnl: Optional[float] = None
    day_unrealized_pnl: Optional[float] = None
    day_total_pnl: Optional[float] = None
    capital_used_trade: Optional[float] = None
    capital_reserved: Optional[float] = None
    capital_released: Optional[float] = None
    capital_used_day: Optional[float] = None
    capital_available: Optional[float] = None
    account_equity: Optional[float] = None
    position_status: Optional[str] = None
    order_status: Optional[str] = None
    execution_mode: Optional[str] = None
    configured_primary_broker: Optional[str] = None
    active_execution_broker: Optional[str] = None
    standby_broker: Optional[str] = None
    delivery_channels: List[str] = field(default_factory=list)
    delivery_status: str = "PERSISTED"
    delivery_attempts: int = 0
    delivery_error: Optional[str] = None
    payload_json: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls,
        notification_type: str,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = NotificationSeverity.INFO.value,
        timezone_name: str = "Asia/Kolkata",
    ) -> "NotificationRecord":
        original_payload = dict(payload or {})
        raw_payload = dict(original_payload)
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(ZoneInfo(timezone_name))
        base: Dict[str, Any] = {
            "notification_id": str(raw_payload.pop("notification_id", uuid.uuid4())),
            "notification_type": str(notification_type),
            "severity": str(raw_payload.pop("severity", severity)),
            "timestamp_utc": str(raw_payload.pop("timestamp_utc", now_utc.isoformat())),
            "timestamp_ist": str(raw_payload.pop("timestamp_ist", now_ist.isoformat())),
            "created_at": str(raw_payload.get("created_at", now_utc.isoformat())),
            "updated_at": str(raw_payload.get("updated_at", now_utc.isoformat())),
        }
        field_names = {item.name for item in fields(cls)}
        for key in list(raw_payload.keys()):
            if key in field_names and key not in {"payload_json"}:
                base[key] = raw_payload.pop(key)
        payload_json = dict(original_payload)
        nested_payload = payload_json.pop("payload_json", None)
        if isinstance(nested_payload, dict):
            payload_json.update(nested_payload)
        base["payload_json"] = payload_json
        return cls(**base)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


__all__ = ["NotificationRecord", "NotificationSeverity", "NotificationType"]
