from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ControlRequest(BaseModel):
    action: str


class OrderResponse(BaseModel):
    status: str
    broker: str
    symbol: str
    quantity: int
    action: str
    price: Optional[float] = None
    mode: Optional[str] = None
    reconciliation: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    mode: str
    execution_mode: str
    configured_primary_broker: str
    active_execution_broker: str
    standby_broker: str
    market_data_mode: str
    primary_market_data_broker: str
    standby_market_data_broker: str
    active_market_data_source: str
    primary_connection_state: str
    standby_connection_state: str
    brokers: Dict[str, Any]
    last_valid_tick: Optional[str] = None
    quote_cache_size: int = 0
    active_subscriptions: int = 0
    stale_instruments: int = 0
    reconnect_count: int = 0
    candle_builder_state: str = "NOT_READY"
    controls: List[str]


class StateResponse(BaseModel):
    lifecycle: Dict[str, Any]
    broker: Dict[str, Any]
    execution_mode: str
    configured_primary_broker: str
    active_execution_broker: str
    standby_broker: str
    brokers: Dict[str, Any]
    market_data_status: Dict[str, Any]
    events: List[Dict[str, Any]]
    orders: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]


class NotificationResponse(BaseModel):
    notification_id: str
    notification_type: str
    severity: str
    timestamp_utc: str
    timestamp_ist: str
    title: str
    summary: str
    delivery_status: str
    payload_json: Dict[str, Any]


class TelemetryEnvelope(BaseModel):
    data: Any


class InstrumentImportRequest(BaseModel):
    source: Optional[str] = None
    path: Optional[str] = None


class MarketDataSubscriptionRequest(BaseModel):
    instrument_ids: List[str]
    consumer: str = "api"
    source: Optional[str] = None
    timeframes: Optional[List[str]] = None


class MarketDataControlRequest(BaseModel):
    source: Optional[str] = None


class ExecutionOrderRequest(BaseModel):
    symbol: str
    quantity: int
    action: str
    price: Optional[float] = None
    idempotency_key: Optional[str] = None


class ExecutionExitRequest(BaseModel):
    trade_id: str
    exit_price: Optional[float] = None
    reason: str = "manual exit"
