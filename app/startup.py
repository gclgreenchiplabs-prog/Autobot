from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.container import AppContainer
from app.event_bus import EventBus
from app.state_store import StateStore


class ApplicationStartupManager:
    def __init__(self, app: FastAPI | None, container: AppContainer | None = None) -> None:
        self.app = app
        self.container = container or AppContainer()
        self.started = False

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncIterator[None]:
        self.app = app
        app.state.container = self.container
        app.state.startup_manager = self
        await self.startup()
        try:
            yield
        finally:
            await self.shutdown()

    async def startup(self) -> None:
        if self.started:
            return
        self.container.repository.initialize_schema()
        self.container.migrations.apply()
        self.container.repository.save_state("lifecycle", {"status": "initialized", "mode": self.container.settings.trading_mode, "kill_switch": False})
        self.container.repository.save_system_event("startup", {"mode": self.container.settings.trading_mode})
        self.container.service_registry = self.container.service_registry or type(self.container.service_registry)()
        try:
            self.container.wire_runtime()
        except ValueError:
            pass
        self.container.notification_service.start()
        self.container.instrument_service.start()
        self.container.health_monitor.record_startup()
        self.container.scheduler.start()
        self.container.task_manager.start()
        self.container.status_scheduler.start()
        self.started = True

    async def shutdown(self) -> None:
        if not self.started:
            return
        self.container.status_scheduler.stop()
        self.container.notification_service.stop()
        self.container.task_manager.cancel_all()
        self.container.scheduler.stop()
        self.container.repository.save_state("lifecycle", {"status": "stopped", "mode": self.container.settings.trading_mode, "kill_switch": False})
        self.container.health_monitor.record_shutdown()
        self.container.repository.save_health_snapshot("STOPPED", {"mode": self.container.settings.trading_mode})
        self.container.database.close()
        self.started = False
