from __future__ import annotations

from typing import Any, Dict

from app.event_bus import EventBus
from app.health import HealthMonitor
from app.notifications.service import NotificationService
from app.scheduler.session_scheduler import SessionScheduler
from app.tasks.manager import BackgroundTaskManager
from app.telemetry import TelemetryService


class DashboardService:
    def __init__(
        self,
        telemetry_service: TelemetryService,
        notification_service: NotificationService,
        event_bus: EventBus,
        health_monitor: HealthMonitor,
        scheduler: SessionScheduler,
        task_manager: BackgroundTaskManager,
    ) -> None:
        self.telemetry_service = telemetry_service
        self.notification_service = notification_service
        self.event_bus = event_bus
        self.health_monitor = health_monitor
        self.scheduler = scheduler
        self.task_manager = task_manager

    def get_state(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="dashboard").to_dict()
        positions = [snapshot.to_dict() for snapshot in self.telemetry_service.build_position_snapshots()]
        recent_exited = [snapshot.to_dict() for snapshot in self.telemetry_service.recent_closed_trades(240)][-5:]
        return {
            "account_summary": account,
            "open_positions": positions,
            "recently_exited": recent_exited,
            "notifications": self.notification_service.latest_notifications(limit=10),
            "detected_events": self.event_bus.list_events()[-10:],
            "health": self.health_monitor.snapshot(),
            "session": self.scheduler.get_state(),
            "tasks": self.task_manager.get_status(),
        }
