from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request

from app.api.controls import ControlService
from app.api.schemas import HealthResponse, StateResponse
from app.container import AppContainer

router = APIRouter()


def _get_container(request: Request) -> AppContainer:
    return request.app.state.container


def _get_control_service(request: Request) -> ControlService:
    return request.app.state.control_service


def _broker_state(container: AppContainer) -> Dict[str, Any]:
    settings = container.settings
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
def health(request: Request) -> HealthResponse:
    broker_state = _broker_state(_get_container(request))
    settings = _get_container(request).settings
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
def get_state(request: Request) -> StateResponse:
    container = _get_container(request)
    broker_state = _broker_state(container)
    lifecycle_state = container.state_store.get("lifecycle") or {"status": "initialized", "mode": container.settings.trading_mode, "kill_switch": False}
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
        events=container.event_bus.list_events(),
        orders=container.state_store.get("orders", []),
        positions=container.state_store.get("positions", []),
    )


@router.get("/api/readiness")
def readiness(request: Request) -> Dict[str, Any]:
    container = _get_container(request)
    broker_state = _broker_state(container)
    return {
        "ready": True,
        "mode": container.settings.trading_mode,
        "execution_mode": broker_state["execution_mode"],
        "configured_primary_broker": broker_state["configured_primary_broker"],
        "active_execution_broker": broker_state["active_execution_broker"],
        "standby_broker": broker_state["standby_broker"],
        "health": container.health_monitor.snapshot(),
    }


@router.get("/api/tasks")
def tasks(request: Request) -> List[Dict[str, Any]]:
    return _get_container(request).task_manager.get_status()


@router.get("/api/session")
def session(request: Request) -> Dict[str, Any]:
    return _get_container(request).scheduler.get_state()


@router.get("/api/database/status")
def database_status(request: Request) -> Dict[str, Any]:
    container = _get_container(request)
    return {"database_path": container.settings.database_path, "ready": True}


@router.get("/api/orders")
def orders(request: Request) -> List[Dict[str, Any]]:
    return _get_container(request).state_store.get("orders", [])


@router.get("/api/positions")
def positions(request: Request) -> List[Dict[str, Any]]:
    return _get_container(request).state_store.get("positions", [])


@router.get("/api/events")
def events(request: Request) -> List[Dict[str, Any]]:
    return _get_container(request).event_bus.list_events()


@router.post("/api/control/start")
def control_start(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("start")


@router.post("/api/control/stop")
def control_stop(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("stop")


@router.post("/api/control/pause")
def control_pause(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("pause")


@router.post("/api/control/resume")
def control_resume(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("resume")


@router.post("/api/control/scan")
def control_scan(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("scan")


@router.post("/api/control/kill-switch")
def control_kill_switch(request: Request) -> Dict[str, Any]:
    return _get_control_service(request).apply("kill-switch")
