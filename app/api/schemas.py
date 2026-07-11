from __future__ import annotations

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


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
    broker: str
    controls: List[str]


class StateResponse(BaseModel):
    lifecycle: Dict[str, Any]
    broker: Dict[str, Any]
    events: List[Dict[str, Any]]
    orders: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]
