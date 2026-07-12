from __future__ import annotations

from typing import Any, Dict

from app.event_bus import EventBus
from app.health import HealthMonitor
from app.instruments.service import InstrumentService
from app.market_data.repository import MarketDataRepository
from app.market_data.service import MarketDataService
from app.notifications.service import NotificationService
from app.scheduler.session_scheduler import SessionScheduler
from app.tasks.manager import BackgroundTaskManager
from app.telemetry import TelemetryService
from app.audit.repository import AuditTimelineRepository


class DashboardService:
    def __init__(
        self,
        telemetry_service: TelemetryService,
        notification_service: NotificationService,
        instrument_service: InstrumentService,
        market_data_repository: MarketDataRepository,
        market_data_service: MarketDataService,
        audit_repository: AuditTimelineRepository,
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        scheduler: SessionScheduler,
        task_manager: BackgroundTaskManager,
    ) -> None:
        self.telemetry_service = telemetry_service
        self.notification_service = notification_service
        self.instrument_service = instrument_service
        self.market_data_repository = market_data_repository
        self.market_data_service = market_data_service
        self.audit_repository = audit_repository
        self.event_bus = event_bus
        self.health_monitor = health_monitor
        self.scheduler = scheduler
        self.task_manager = task_manager

    def get_state(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="dashboard").to_dict()
        positions = [snapshot.to_dict() for snapshot in self.telemetry_service.build_position_snapshots()]
        recent_exited = [snapshot.to_dict() for snapshot in self.telemetry_service.recent_closed_trades(240)][-5:]
        universe_status = self.instrument_service.universe_status()
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
            "audit_timeline": self.audit_repository.list_entries(limit=20),
            "health": self.health_monitor.snapshot(),
            "session": self.scheduler.get_state(),
            "tasks": self.task_manager.get_status(),
        }
