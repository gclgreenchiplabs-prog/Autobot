from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MigrationRecord:
    version: str


@dataclass
class LifecycleEventRecord:
    event_type: str
    payload: Dict[str, Any]


@dataclass
class HealthSnapshotRecord:
    status: str
    details: Dict[str, Any]
