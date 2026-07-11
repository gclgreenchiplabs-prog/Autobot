from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.controls import ControlService
from app.api.schemas import ControlRequest, HealthResponse, StateResponse
from app.brokers.idempotency import IdempotencyStore
from app.brokers.reconciliation import ReconciliationState
from app.brokers.router import BrokerRouter
from app.event_bus import EventBus
from app.lifecycle import AppLifecycle
from app.models import OrderRequest
from app.settings import Settings
from app.state_store import StateStore

router = APIRouter()
state_store = StateStore()
lifecycle = AppLifecycle(state_store=state_store)
control_service = ControlService(state_store=state_store)
event_bus = EventBus()
idempotency_store = IdempotencyStore()
reconciliation_state = ReconciliationState()
settings = Settings()
broker_router = BrokerRouter(settings=settings)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        mode=settings.trading_mode,
        broker=settings.primary_broker,
        controls=["start", "stop", "pause", "resume", "scan", "kill-switch"],
    )


@router.get("/api/state", response_model=StateResponse)
def get_state() -> StateResponse:
    lifecycle_state = state_store.get("lifecycle") or {"status": "initialized", "mode": settings.trading_mode, "kill_switch": False}
    return StateResponse(
        lifecycle=lifecycle_state,
        broker={"name": broker_router.create_broker().name, "mode": settings.trading_mode, "connected": True},
        events=event_bus.list_events(),
        orders=state_store.get("orders", []),
        positions=state_store.get("positions", []),
    )


@router.get("/api/readiness")
def readiness() -> Dict[str, Any]:
    return {"ready": True, "mode": settings.trading_mode, "broker": settings.primary_broker}


@router.get("/api/orders")
def orders() -> List[Dict[str, Any]]:
    return state_store.get("orders", [])


@router.get("/api/positions")
def positions() -> List[Dict[str, Any]]:
    return state_store.get("positions", [])


@router.get("/api/events")
def events() -> List[Dict[str, Any]]:
    return event_bus.list_events()


@router.post("/api/control/start")
def control_start() -> Dict[str, Any]:
    return control_service.apply("start")


@router.post("/api/control/stop")
def control_stop() -> Dict[str, Any]:
    return control_service.apply("stop")


@router.post("/api/control/pause")
def control_pause() -> Dict[str, Any]:
    return control_service.apply("pause")


@router.post("/api/control/resume")
def control_resume() -> Dict[str, Any]:
    return control_service.apply("resume")


@router.post("/api/control/scan")
def control_scan() -> Dict[str, Any]:
    return control_service.apply("scan")


@router.post("/api/control/kill-switch")
def control_kill_switch() -> Dict[str, Any]:
    return control_service.apply("kill-switch")


@router.post("/api/orders")
def create_order(payload: ControlRequest) -> Dict[str, Any]:
    order = OrderRequest(symbol="NIFTY", quantity=1, action="buy")
    result = broker_router.place_order(
        order,
        idempotency_key=payload.action,
        idempotency_store=idempotency_store,
        reconciliation_state=reconciliation_state,
    )
    orders = state_store.get("orders", [])
    orders.append(result)
    state_store.set("orders", orders)
    event_bus.publish({"type": "order", "payload": result})
    return result
