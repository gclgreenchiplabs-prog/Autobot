from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import HealthResponse, StateResponse
from app.container import AppContainer

router = APIRouter()


def _get_container(request: Request) -> AppContainer:
    return request.app.state.container


def _get_control_service(request: Request) -> Any:
    return request.app.state.control_service


def _get_notification_service(request: Request) -> Any:
    return request.app.state.notification_service


def _get_telemetry_service(request: Request) -> Any:
    return request.app.state.telemetry_service


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
    container = _get_container(request)
    broker_state = _broker_state(container)
    settings = container.settings
    return HealthResponse(
        status="ok",
        mode=settings.trading_mode,
        execution_mode=broker_state["execution_mode"],
        configured_primary_broker=broker_state["configured_primary_broker"],
        active_execution_broker=broker_state["active_execution_broker"],
        standby_broker=broker_state["standby_broker"],
        controls=["start", "stop", "pause", "resume", "scan", "kill-switch", "send-status-now"],
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


@router.get("/api/notifications")
def list_notifications(
    request: Request,
    notification_type: Optional[str] = None,
    severity: Optional[str] = None,
    symbol: Optional[str] = None,
    trade_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    return _get_notification_service(request).list_notifications(
        notification_type=notification_type,
        severity=severity,
        symbol=symbol,
        trade_id=trade_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )


@router.get("/api/notifications/latest")
def latest_notifications(request: Request, limit: int = Query(default=10, ge=1, le=100)) -> List[Dict[str, Any]]:
    return _get_notification_service(request).latest_notifications(limit=limit)


@router.get("/api/notifications/trade/{trade_id}")
def notifications_by_trade(request: Request, trade_id: str, limit: int = Query(default=50, ge=1, le=100)) -> List[Dict[str, Any]]:
    return _get_notification_service(request).notifications_by_trade(trade_id=trade_id, limit=limit)


@router.get("/api/notifications/symbol/{symbol}")
def notifications_by_symbol(request: Request, symbol: str, limit: int = Query(default=50, ge=1, le=100)) -> List[Dict[str, Any]]:
    return _get_notification_service(request).notifications_by_symbol(symbol=symbol, limit=limit)


@router.get("/api/notifications/{notification_id}")
def notification_by_id(request: Request, notification_id: str) -> Dict[str, Any]:
    notification = _get_notification_service(request).get_notification(notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return notification


@router.get("/api/telemetry/account")
def telemetry_account(request: Request) -> Dict[str, Any]:
    return _get_telemetry_service(request).build_account_snapshot(reason="api").to_dict()


@router.get("/api/telemetry/positions")
def telemetry_positions(request: Request) -> List[Dict[str, Any]]:
    return [snapshot.to_dict() for snapshot in _get_telemetry_service(request).build_position_snapshots()]


@router.get("/api/telemetry/trades")
def telemetry_trades(request: Request) -> List[Dict[str, Any]]:
    return [snapshot.to_dict() for snapshot in _get_telemetry_service(request).build_trade_snapshots()]


@router.get("/api/telemetry/day-summary")
def telemetry_day_summary(request: Request) -> Dict[str, Any]:
    return _get_telemetry_service(request).build_day_summary().to_dict()


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


@router.post("/api/control/send-status-now")
def control_send_status_now(request: Request) -> Dict[str, Any]:
    notification = _get_notification_service(request).generate_status_report(force=True, source="manual")
    if notification is None:
        raise HTTPException(status_code=503, detail="status report was not generated")
    return notification
