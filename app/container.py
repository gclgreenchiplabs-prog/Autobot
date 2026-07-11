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
from app.scheduler.market_clock import MarketClock
from app.scheduler.session_scheduler import SessionScheduler
from app.services.registry import ServiceRegistry
from app.state_store import StateStore
from app.tasks.manager import BackgroundTaskManager
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
        self.health_monitor = HealthMonitor(self.settings, self.database, self.state_store)
        self.market_clock = MarketClock(self.settings)
        self.scheduler = SessionScheduler(self.market_clock, self.state_store)
        self.task_manager = BackgroundTaskManager()
        self.service_registry = ServiceRegistry()

    def wire_runtime(self) -> None:
        self.service_registry.register("database", self.database)
        self.service_registry.register("state_store", self.state_store)
        self.service_registry.register("broker_router", self.broker_router)
        self.service_registry.register("scheduler", self.scheduler)
        self.service_registry.register("task_manager", self.task_manager)
        self.service_registry.register("health_monitor", self.health_monitor)
