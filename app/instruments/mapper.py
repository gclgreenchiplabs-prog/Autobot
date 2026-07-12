from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional


def resolve_mapping_status(
    *,
    broker: str,
    broker_symbol: Optional[str],
    broker_security_id: Optional[str],
    exchange_token: Optional[str],
    last_verified_timestamp: Optional[str],
    not_configured: bool = False,
    conflict: bool = False,
    max_age_hours: int = 24,
) -> str:
    if not_configured:
        return "NOT_CONFIGURED"
    if conflict:
        return "CONFLICT"
    if not any([broker_symbol, broker_security_id, exchange_token]):
        return "MISSING"
    if not all([broker_symbol, broker_security_id or broker == "fyers"]):
        return "PARTIAL"
    if last_verified_timestamp:
        verified = datetime.fromisoformat(last_verified_timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        age_hours = (datetime.now(timezone.utc) - verified).total_seconds() / 3600
        if age_hours > max_age_hours:
            return "STALE"
    return "READY"


def summarize_mapping_states(mappings: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for mapping in mappings:
        broker = str(mapping.get("broker") or "unknown").lower()
        status = str(mapping.get("mapping_status") or "MISSING").upper()
        broker_summary = summary.setdefault(broker, {"READY": 0, "PARTIAL": 0, "MISSING": 0, "CONFLICT": 0, "STALE": 0, "NOT_CONFIGURED": 0})
        broker_summary.setdefault(status, 0)
        broker_summary[status] += 1
    return summary
