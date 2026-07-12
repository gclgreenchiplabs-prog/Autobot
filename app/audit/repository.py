from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.audit.timeline import AuditTimelineEntry
from app.database.repository import Repository


class AuditTimelineRepository:
    def __init__(self, repository: Repository, timezone_name: str = "Asia/Kolkata") -> None:
        self.repository = repository
        self.timezone_name = timezone_name

    def record(self, **kwargs: Any) -> Dict[str, Any]:
        entry = AuditTimelineEntry.create(timezone_name=self.timezone_name, **kwargs)
        self.repository.save_decision_timeline(entry.to_dict())
        return entry.to_dict()

    def list_entries(
        self,
        *,
        trade_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        instrument_id: Optional[str] = None,
        module: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_decision_timeline(
            trade_id=trade_id,
            candidate_id=candidate_id,
            instrument_id=instrument_id,
            module=module,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
