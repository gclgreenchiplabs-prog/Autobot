from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.api.schemas import HealthResponse, InstrumentImportRequest, MarketDataControlRequest, MarketDataSubscriptionRequest, StateResponse
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


def _get_instrument_service(request: Request) -> Any:
    return request.app.state.instrument_service


def _get_market_data_repository(request: Request) -> Any:
    return request.app.state.market_data_repository


def _get_market_data_service(request: Request) -> Any:
    return request.app.state.market_data_service


def _get_broker_readiness_service(request: Request) -> Any:
    return request.app.state.broker_readiness_service


def _get_audit_repository(request: Request) -> Any:
    return request.app.state.audit_repository


def _broker_state(container: AppContainer) -> Dict[str, Any]:
    settings = container.settings
    if settings.is_paper_mode:
        return {
            "execution_mode": "paper",
            "configured_primary_broker": settings.primary_broker,
            "active_execution_broker": "paper",
            "standby_broker": settings.standby_broker,
        }

    return {
        "execution_mode": settings.trading_mode,
        "configured_primary_broker": settings.primary_broker,
        "active_execution_broker": settings.execution_broker,
        "standby_broker": settings.standby_broker,
    }


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    container = _get_container(request)
    broker_state = _broker_state(container)
    settings = container.settings
    market_data = _get_market_data_service(request).status()
    brokers = _get_broker_readiness_service(request).refresh()
    heartbeat = market_data.get("heartbeat") or {}
    return HealthResponse(
        status="ok",
        mode=settings.trading_mode,
        execution_mode=broker_state["execution_mode"],
        configured_primary_broker=broker_state["configured_primary_broker"],
        active_execution_broker=broker_state["active_execution_broker"],
        standby_broker=broker_state["standby_broker"],
        market_data_mode=market_data["market_data_mode"],
        primary_market_data_broker=market_data["primary_market_data_broker"],
        standby_market_data_broker=market_data["standby_market_data_broker"],
        active_market_data_source=market_data["active_market_data_source"],
        primary_connection_state=market_data["primary_connection_state"],
        standby_connection_state=market_data["standby_connection_state"],
        brokers=brokers,
        last_valid_tick=heartbeat.get("last_valid_tick"),
        quote_cache_size=market_data["quote_cache_size"],
        active_subscriptions=market_data["active_subscriptions"],
        stale_instruments=market_data["stale_instruments"],
        reconnect_count=heartbeat.get("reconnect_count", 0),
        candle_builder_state=market_data["candle_builder_state"],
        controls=[
            "start",
            "stop",
            "pause",
            "resume",
            "scan",
            "kill-switch",
            "send-status-now",
            "import-instruments",
            "market-data/connect",
            "market-data/disconnect",
            "market-data/subscribe",
            "market-data/unsubscribe",
            "market-data/reconnect",
            "market-data/start-fixture",
            "market-data/stop-fixture",
        ],
    )


@router.get("/api/state", response_model=StateResponse)
def get_state(request: Request) -> StateResponse:
    container = _get_container(request)
    broker_state = _broker_state(container)
    lifecycle_state = container.state_store.get("lifecycle") or {"status": "initialized", "mode": container.settings.trading_mode, "kill_switch": False}
    brokers = _get_broker_readiness_service(request).refresh()
    active_broker = broker_state["active_execution_broker"]
    active_connected = False if active_broker == "paper" else bool((brokers.get(active_broker) or {}).get("connected"))
    return StateResponse(
        lifecycle=lifecycle_state,
        broker={
            "name": active_broker,
            "mode": broker_state["execution_mode"],
            "connected": active_connected,
        },
        execution_mode=broker_state["execution_mode"],
        configured_primary_broker=broker_state["configured_primary_broker"],
        active_execution_broker=broker_state["active_execution_broker"],
        standby_broker=broker_state["standby_broker"],
        brokers=brokers,
        market_data_status=_get_market_data_service(request).status(),
        events=container.event_bus.list_events(),
        orders=container.state_store.get("orders", []),
        positions=container.state_store.get("positions", []),
    )


@router.get("/api/readiness")
def readiness(request: Request) -> Dict[str, Any]:
    container = _get_container(request)
    broker_state = _broker_state(container)
    brokers = _get_broker_readiness_service(request).refresh()
    return {
        "ready": True,
        "mode": container.settings.trading_mode,
        "execution_mode": broker_state["execution_mode"],
        "market_data_mode": container.settings.market_data_mode.lower(),
        "configured_primary_broker": broker_state["configured_primary_broker"],
        "active_execution_broker": broker_state["active_execution_broker"],
        "standby_broker": broker_state["standby_broker"],
        "primary_market_data_broker": container.settings.primary_market_data_broker,
        "active_market_data_source": _get_market_data_service(request).status().get("active_market_data_source"),
        "standby_market_data_broker": container.settings.standby_market_data_broker,
        "brokers": brokers,
        "health": container.health_monitor.snapshot(),
        "universe": container.state_store.get("universe_status") or {},
        "market_data": _get_market_data_service(request).status(),
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


@router.get("/api/companies")
def companies(
    request: Request,
    exchange: Optional[str] = None,
    active: Optional[bool] = None,
    symbol: Optional[str] = None,
    isin: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).list_companies(
        exchange=exchange,
        active=active,
        symbol=symbol,
        isin=isin,
        limit=limit,
        offset=offset,
    )


@router.get("/api/companies/{company_id}")
def company_by_id(request: Request, company_id: str) -> Dict[str, Any]:
    company = _get_instrument_service(request).get_company(company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    return company


@router.get("/api/instruments")
def instruments(
    request: Request,
    exchange: Optional[str] = None,
    segment: Optional[str] = None,
    instrument_type: Optional[str] = None,
    fno_eligible: Optional[bool] = None,
    active: Optional[bool] = None,
    symbol: Optional[str] = None,
    isin: Optional[str] = None,
    broker: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).list_instruments(
        exchange=exchange,
        segment=segment,
        instrument_type=instrument_type,
        fno_eligible=fno_eligible,
        active=active,
        symbol=symbol,
        isin=isin,
        broker=broker,
        limit=limit,
        offset=offset,
    )


@router.get("/api/instruments/{instrument_id}")
def instrument_by_id(request: Request, instrument_id: str) -> Dict[str, Any]:
    instrument = _get_instrument_service(request).get_instrument(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return instrument


@router.get("/api/universe/status")
def universe_status(request: Request) -> Dict[str, Any]:
    return _get_instrument_service(request).universe_status()


@router.get("/api/universe/conflicts")
def universe_conflicts(request: Request) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).repository.list_conflicts()


@router.get("/api/universe/fno")
def universe_fno(request: Request, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).list_instruments(fno_eligible=True, limit=limit, offset=offset)


@router.get("/api/universe/nse")
def universe_nse(request: Request, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).list_instruments(exchange="NSE", limit=limit, offset=offset)


@router.get("/api/universe/bse")
def universe_bse(request: Request, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).list_instruments(exchange="BSE", limit=limit, offset=offset)


@router.get("/api/market-data/quality")
def market_data_quality(
    request: Request,
    quality_class: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[Dict[str, Any]]:
    return _get_market_data_repository(request).list_quality(quality_class=quality_class, limit=limit, offset=offset)


@router.get("/api/market-data/stale")
def market_data_stale(request: Request, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)) -> List[Dict[str, Any]]:
    return _get_market_data_repository(request).list_staleness(limit=limit, offset=offset)


@router.get("/api/market-data/liquidity")
def market_data_liquidity(
    request: Request,
    liquidity_class: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> List[Dict[str, Any]]:
    return _get_market_data_repository(request).list_liquidity(liquidity_class=liquidity_class, limit=limit, offset=offset)


@router.get("/api/market-data/status")
def market_data_status(request: Request) -> Dict[str, Any]:
    return {
        **_get_market_data_service(request).status(),
        "brokers": _get_broker_readiness_service(request).refresh(),
    }


@router.get("/api/market-data/connections")
def market_data_connections(request: Request) -> Dict[str, Any]:
    return {
        "connections": _get_market_data_service(request).connections(),
        "brokers": _get_broker_readiness_service(request).refresh(),
    }


@router.get("/api/market-data/subscriptions")
def market_data_subscriptions(request: Request) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).subscriptions()


@router.get("/api/market-data/quotes")
def market_data_quotes(request: Request) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).quotes()


@router.get("/api/market-data/quotes/{instrument_id}")
def market_data_quote_by_instrument(request: Request, instrument_id: str) -> Dict[str, Any]:
    quote = _get_market_data_service(request).quotes(instrument_id=instrument_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="quote not found")
    return quote


@router.get("/api/market-data/candles")
def market_data_candles(
    request: Request,
    instrument_id: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).candles(instrument_id=instrument_id, timeframe=timeframe, limit=limit)


@router.get("/api/market-data/candles/{instrument_id}")
def market_data_candles_by_instrument(
    request: Request,
    instrument_id: str,
    timeframe: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).candles(instrument_id=instrument_id, timeframe=timeframe, limit=limit)


@router.get("/api/market-data/rejections")
def market_data_rejections(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).rejections(limit=limit)


@router.get("/api/market-data/events")
def market_data_events(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> List[Dict[str, Any]]:
    return _get_market_data_service(request).events(limit=limit)


@router.get("/api/market-data/heartbeat")
def market_data_heartbeat(request: Request) -> Dict[str, Any]:
    return _get_market_data_service(request).heartbeat_snapshot()


@router.get("/api/audit/timeline")
def audit_timeline(
    request: Request,
    trade_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    instrument_id: Optional[str] = None,
    module: Optional[str] = None,
    event_type: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> List[Dict[str, Any]]:
    return _get_audit_repository(request).list_entries(
        trade_id=trade_id,
        candidate_id=candidate_id,
        instrument_id=instrument_id,
        module=module,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )


@router.get("/api/scanner/candidates")
def scanner_candidates(request: Request) -> List[Dict[str, Any]]:
    return _get_instrument_service(request).repository.list_candidates()


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


@router.post("/api/control/import-instruments")
def control_import_instruments(request: Request, payload: Optional[InstrumentImportRequest] = Body(default=None)) -> Dict[str, Any]:
    body = payload.model_dump(exclude_none=True) if payload is not None else {}
    return _get_instrument_service(request).import_instruments(body)


@router.post("/api/control/market-data/connect")
def control_market_data_connect(request: Request, payload: Optional[MarketDataControlRequest] = Body(default=None)) -> Dict[str, Any]:
    body = payload.model_dump(exclude_none=True) if payload is not None else {}
    try:
        result = _get_market_data_service(request).connect(body.get("source"))
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/disconnect")
def control_market_data_disconnect(request: Request, payload: Optional[MarketDataControlRequest] = Body(default=None)) -> Dict[str, Any]:
    body = payload.model_dump(exclude_none=True) if payload is not None else {}
    try:
        result = _get_market_data_service(request).disconnect(body.get("source"))
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/reconnect")
def control_market_data_reconnect(request: Request, payload: Optional[MarketDataControlRequest] = Body(default=None)) -> Dict[str, Any]:
    body = payload.model_dump(exclude_none=True) if payload is not None else {}
    try:
        result = _get_market_data_service(request).reconnect(body.get("source"))
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/subscribe")
def control_market_data_subscribe(request: Request, payload: MarketDataSubscriptionRequest) -> Dict[str, Any]:
    try:
        result = _get_market_data_service(request).subscribe(
            instrument_ids=payload.instrument_ids,
            consumer=payload.consumer,
            source=payload.source,
            timeframes=payload.timeframes,
        )
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/unsubscribe")
def control_market_data_unsubscribe(request: Request, payload: MarketDataSubscriptionRequest) -> Dict[str, Any]:
    try:
        result = _get_market_data_service(request).unsubscribe(
            instrument_ids=payload.instrument_ids,
            consumer=payload.consumer,
            source=payload.source,
        )
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/start-fixture")
def control_market_data_start_fixture(request: Request) -> Dict[str, Any]:
    try:
        result = _get_market_data_service(request).start_fixture()
        _get_broker_readiness_service(request).refresh()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/control/market-data/stop-fixture")
def control_market_data_stop_fixture(request: Request) -> Dict[str, Any]:
    result = _get_market_data_service(request).stop_fixture()
    _get_broker_readiness_service(request).refresh()
    return result
