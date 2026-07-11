from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TaskRecord:
    name: str
    state: str = "REGISTERED"
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None


class BackgroundTaskManager:
    def __init__(self) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._loop = None

    def register(self, name: str, coro_factory: Callable[[], Any]) -> TaskRecord:
        if name in self._tasks:
            raise ValueError("Duplicate task name")
        record = TaskRecord(name=name)
        self._tasks[name] = record
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            try:
                asyncio.run(self._run_task(name, coro_factory))
            except RuntimeError:
                record.state = "REGISTERED"
                return record
            record.state = self._tasks[name].state
            return record
        self._loop = self._loop or loop
        record.task = self._loop.create_task(self._run_task(name, coro_factory))
        record.state = "RUNNING"
        return record

    async def _run_task(self, name: str, coro_factory: Callable[[], Any]) -> None:
        try:
            await coro_factory()
            self._tasks[name].state = "COMPLETED"
        except Exception as exc:
            self._tasks[name].state = "FAILED"
            self._tasks[name].error = repr(exc)

    def start(self) -> None:
        return None

    def set_state(self, name: str, state: str, error: Optional[str] = None) -> TaskRecord:
        record = self._tasks.get(name)
        if record is None:
            record = TaskRecord(name=name)
            self._tasks[name] = record
        record.state = state
        record.error = error
        return record

    def stop(self, name: str) -> None:
        record = self._tasks.get(name)
        if record is None:
            return
        if record.task is not None:
            record.task.cancel()
        record.state = "CANCELLED"

    def cancel_all(self) -> None:
        for record in self._tasks.values():
            if record.task is not None:
                record.task.cancel()
            record.state = "CANCELLED"

    def get_status(self) -> List[Dict[str, Any]]:
        return [
            {"name": record.name, "state": record.state, "error": record.error}
            for record in self._tasks.values()
        ]

    def get_task(self, name: str) -> Optional[TaskRecord]:
        return self._tasks.get(name)
