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
    controls: List[str]


class StateResponse(BaseModel):
    lifecycle: Dict[str, Any]
    broker: Dict[str, Any]
    execution_mode: str
    configured_primary_broker: str
    active_execution_broker: str
    standby_broker: str
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
