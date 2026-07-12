from __future__ import annotations

from typing import Any, Dict

from app.event_bus import EventBus
from app.health import HealthMonitor
from app.instruments.service import InstrumentService
from app.market_data.repository import MarketDataRepository
from app.market_data.service import MarketDataService
from app.notifications.service import NotificationService
from app.scanners.scanner_engine import ScannerEngine
from app.scheduler.session_scheduler import SessionScheduler
from app.tasks.manager import BackgroundTaskManager
from app.telemetry import TelemetryService
from app.audit.repository import AuditTimelineRepository
from app.execution.service import ExecutionService


class DashboardService:
    def __init__(
        self,
        telemetry_service: TelemetryService,
        notification_service: NotificationService,
        instrument_service: InstrumentService,
        market_data_repository: MarketDataRepository,
        market_data_service: MarketDataService,
        scanner_engine: ScannerEngine,
        audit_repository: AuditTimelineRepository,
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        scheduler: SessionScheduler,
        task_manager: BackgroundTaskManager,
        execution_service: ExecutionService,
    ) -> None:
        self.telemetry_service = telemetry_service
        self.notification_service = notification_service
        self.instrument_service = instrument_service
        self.market_data_repository = market_data_repository
        self.market_data_service = market_data_service
        self.scanner_engine = scanner_engine
        self.audit_repository = audit_repository
        self.event_bus = event_bus
        self.health_monitor = health_monitor
        self.scheduler = scheduler
        self.task_manager = task_manager
        self.execution_service = execution_service

    def get_state(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="dashboard").to_dict()
        positions = [snapshot.to_dict() for snapshot in self.telemetry_service.build_position_snapshots()]
        recent_exited = [snapshot.to_dict() for snapshot in self.telemetry_service.recent_closed_trades(240)][-5:]
        universe_status = self.instrument_service.universe_status()
        health = self.health_monitor.snapshot()
        scanner_state = self.scanner_engine.refresh(reason="dashboard")
        return {
            "account_summary": account,
            "open_positions": positions,
            "recently_exited": recent_exited,
            "notifications": self.notification_service.latest_notifications(limit=10),
            "detected_events": self.event_bus.list_events()[-10:],
            "universe_summary": universe_status,
            "broker_mapping_summary": universe_status["broker_mapping_summary"],
            "data_quality_summary": universe_status["quality_class_counts"],
            "liquidity_summary": universe_status["liquidity_class_counts"],
            "stale_data_summary": universe_status["stale_state_counts"],
            "instrument_table": self.instrument_service.list_instruments(limit=20, offset=0),
            "conflicts": self.instrument_service.repository.list_conflicts(),
            "market_data_status": self.market_data_service.status(),
            "market_data_connections": self.market_data_service.connections(),
            "market_data_subscriptions": self.market_data_service.subscriptions(),
            "market_data_quotes": self.market_data_service.quotes(),
            "market_data_candles": self.market_data_service.candles(limit=20),
            "market_data_events": self.market_data_service.events(limit=20),
            "market_data_heartbeat": self.market_data_service.heartbeat_snapshot(),
            "scanner_summary": scanner_state["summary"],
            "scanner_regime": scanner_state["regime"],
            "scanner_intraday": scanner_state["intraday"],
            "scanner_btst": scanner_state["btst"],
            "scanner_swing": scanner_state["swing"],
            "scanner_portfolio": scanner_state["portfolio"],
            "scanner_options": scanner_state["options"],
            "scanner_watchlist": scanner_state["watchlist"],
            "scanner_avoid": scanner_state["avoid"],
            "scanner_corporate_events": scanner_state["corporate_events"],
            "scanner_sector_rotation": scanner_state["sector_rotation"],
            "scanner_risk_heatmap": scanner_state["risk_heatmap"],
            "scanner_top_gainers": scanner_state["top_gainers"],
            "scanner_top_losers": scanner_state["top_losers"],
            "broker_readiness": health.get("brokers", {}),
            "audit_timeline": self.audit_repository.list_entries(limit=20),
            "health": health,
            "session": self.scheduler.get_state(),
            "tasks": self.task_manager.get_status(),
            "execution_status": self.execution_service.status(),
        }
