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


def _broker_state() -> Dict[str, Any]:
    if settings.is_paper_mode:
        return {
            "execution_mode": "paper",
            "configured_primary_broker": "fyers",
            "active_execution_broker": "paper",
            "standby_broker": "dhan",
        }

    return {
        "execution_mode": settings.trading_mode,
        "configured_primary_broker": settings.primary_broker,
        "active_execution_broker": settings.primary_broker,
        "standby_broker": settings.standby_broker,
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    broker_state = _broker_state()
    return HealthResponse(
        status="ok",
        mode=settings.trading_mode,
        execution_mode=broker_state["execution_mode"],
        configured_primary_broker=broker_state["configured_primary_broker"],
        active_execution_broker=broker_state["active_execution_broker"],
        standby_broker=broker_state["standby_broker"],
        controls=["start", "stop", "pause", "resume", "scan", "kill-switch"],
    )


@router.get("/api/state", response_model=StateResponse)
def get_state() -> StateResponse:
    lifecycle_state = state_store.get("lifecycle") or {"status": "initialized", "mode": settings.trading_mode, "kill_switch": False}
    broker_state = _broker_state()
    return StateResponse(
        lifecycle=lifecycle_state,
        broker={
            "name": broker_state["active_execution_broker"],
            "mode": broker_state["execution_mode"],
            "connected": broker_state["execution_mode"] == "live",
        },
        execution_mode=broker_state["execution_mode"],
        configured_primary_broker=broker_state["configured_primary_broker"],
        active_execution_broker=broker_state["active_execution_broker"],
        standby_broker=broker_state["standby_broker"],
        events=event_bus.list_events(),
        orders=state_store.get("orders", []),
        positions=state_store.get("positions", []),
    )


@router.get("/api/readiness")
def readiness() -> Dict[str, Any]:
    broker_state = _broker_state()
    return {
        "ready": True,
        "mode": settings.trading_mode,
        "execution_mode": broker_state["execution_mode"],
        "configured_primary_broker": broker_state["configured_primary_broker"],
        "active_execution_broker": broker_state["active_execution_broker"],
        "standby_broker": broker_state["standby_broker"],
    }


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
