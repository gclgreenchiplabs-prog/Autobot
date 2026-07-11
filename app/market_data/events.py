from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def market_data_event(
    event_type: str,
    *,
    source: str,
    severity: str,
    title: str,
    description: str,
    instrument_id: Optional[str] = None,
    symbol: Optional[str] = None,
    reason: Optional[str] = None,
    action_taken: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "event_id": f"{source}-{event_type.lower()}-{datetime.now(timezone.utc).timestamp()}",
        "event_type": event_type,
        "source": source,
        "severity": severity,
        "title": title,
        "description": description,
        "instrument_id": instrument_id,
        "symbol": symbol,
        "reason": reason,
        "action_taken": action_taken,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
