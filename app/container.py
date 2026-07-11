from __future__ import annotations

from app.brokers.idempotency import IdempotencyStore
from app.brokers.reconciliation import ReconciliationState
from app.brokers.router import BrokerRouter
from app.database.connection import DatabaseConnection
from app.database.migrations import MigrationRunner
from app.database.repository import Repository
from app.event_bus import EventBus
from app.health import HealthMonitor
from app.lifecycle import AppLifecycle
from app.logging_setup import configure_logging
from app.notifications import (
    NotificationDispatcher,
    NotificationFormatter,
    NotificationRepository,
    NotificationService,
    StatusNotificationScheduler,
    TelegramAdapter,
)
from app.api.controls import ControlService
from app.scheduler.market_clock import MarketClock
from app.scheduler.session_scheduler import SessionScheduler
from app.services.registry import ServiceRegistry
from app.state_store import StateStore
from app.tasks.manager import BackgroundTaskManager
from app.telemetry import TelemetryService
from app.dashboard.service import DashboardService
from app.settings import Settings, validate_settings


class AppContainer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        validate_settings(self.settings)
        configure_logging(log_dir="logs")
        self.database = DatabaseConnection(self.settings.database_path)
        self.state_store = StateStore()
        self.event_bus = EventBus()
        self.lifecycle = AppLifecycle(state_store=self.state_store)
        self.broker_router = BrokerRouter(settings=self.settings)
        self.idempotency_store = IdempotencyStore()
        self.reconciliation = ReconciliationState()
        self.repository = Repository(self.database)
        self.migrations = MigrationRunner(self.database)
        self.repository.initialize_schema()
        self.migrations.apply()
        self.health_monitor = HealthMonitor(self.settings, self.database, self.state_store)
        self.market_clock = MarketClock(self.settings)
        self.scheduler = SessionScheduler(self.market_clock, self.state_store)
        self.task_manager = BackgroundTaskManager()
        self.service_registry = ServiceRegistry()
        self.telemetry_service = TelemetryService(self.settings, self.state_store, self.repository, self.event_bus)
        self.notification_repository = NotificationRepository(self.repository)
        self.notification_formatter = NotificationFormatter()
        self.telegram_adapter = TelegramAdapter(self.settings)
        self.notification_dispatcher = NotificationDispatcher(self.notification_repository, self.telegram_adapter)
        self.notification_service = NotificationService(
            settings=self.settings,
            state_store=self.state_store,
            notification_repository=self.notification_repository,
            telemetry_service=self.telemetry_service,
            formatter=self.notification_formatter,
            dispatcher=self.notification_dispatcher,
            event_bus=self.event_bus,
            scheduler=self.scheduler,
            health_monitor=self.health_monitor,
        )
        self.status_scheduler = StatusNotificationScheduler(
            notification_service=self.notification_service,
            task_manager=self.task_manager,
            interval_minutes=self.settings.status_notification_interval_minutes,
        )
        self.control_service = ControlService(
            state_store=self.state_store,
            notification_service=self.notification_service,
        )
        self.dashboard_service = DashboardService(
            telemetry_service=self.telemetry_service,
            notification_service=self.notification_service,
            event_bus=self.event_bus,
            health_monitor=self.health_monitor,
            scheduler=self.scheduler,
            task_manager=self.task_manager,
        )

    def wire_runtime(self) -> None:
        self.service_registry.register("database", self.database)
        self.service_registry.register("state_store", self.state_store)
        self.service_registry.register("broker_router", self.broker_router)
        self.service_registry.register("scheduler", self.scheduler)
        self.service_registry.register("task_manager", self.task_manager)
        self.service_registry.register("health_monitor", self.health_monitor)
        self.service_registry.register("telemetry_service", self.telemetry_service)
        self.service_registry.register("notification_service", self.notification_service)
