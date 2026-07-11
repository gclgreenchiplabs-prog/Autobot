from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


@dataclass
class AuditTimelineEntry:
    timeline_id: str
    correlation_id: Optional[str]
    trade_id: Optional[str]
    candidate_id: Optional[str]
    instrument_id: Optional[str]
    timestamp_utc: str
    timestamp_ist: str
    module: str
    event_type: str
    previous_value_json: Dict[str, Any] = field(default_factory=dict)
    new_value_json: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    metrics_json: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    created_at: str = ""

    @classmethod
    def create(
        cls,
        *,
        module: str,
        event_type: str,
        timezone_name: str = "Asia/Kolkata",
        correlation_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        instrument_id: Optional[str] = None,
        previous_value_json: Optional[Dict[str, Any]] = None,
        new_value_json: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        metrics_json: Optional[Dict[str, Any]] = None,
        source: str = "system",
    ) -> "AuditTimelineEntry":
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(ZoneInfo(timezone_name))
        return cls(
            timeline_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trade_id=trade_id,
            candidate_id=candidate_id,
            instrument_id=instrument_id,
            timestamp_utc=now_utc.isoformat(),
            timestamp_ist=now_ist.isoformat(),
            module=module,
            event_type=event_type,
            previous_value_json=previous_value_json or {},
            new_value_json=new_value_json or {},
            reason=reason,
            metrics_json=metrics_json or {},
            source=source,
            created_at=now_utc.isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
