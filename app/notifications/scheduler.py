from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from app.notifications.service import NotificationService
from app.tasks.manager import BackgroundTaskManager


class StatusNotificationScheduler:
    def __init__(
        self,
        notification_service: NotificationService,
        task_manager: BackgroundTaskManager,
        interval_minutes: int,
    ) -> None:
        self.notification_service = notification_service
        self.task_manager = task_manager
        self.interval_seconds = max(interval_minutes, 1) * 60
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.task_manager.set_state("status-notifications", "RUNNING")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self.task_manager.set_state("status-notifications", "REGISTERED")
            return
        self._task = loop.create_task(self._run_loop())

    def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None
        self.task_manager.set_state("status-notifications", "CANCELLED")

    async def _run_loop(self) -> None:
        while self._running:
            await self.run_once()
            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> Optional[Dict[str, Any]]:
        return self.notification_service.generate_status_report(force=False, source="scheduler")

    def status(self) -> Dict[str, Any]:
        return {"running": self._running, "interval_seconds": self.interval_seconds}
