from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def evaluate_staleness(
    *,
    timestamp_utc: str,
    import_timestamp: str,
    mapping_age_hours: float,
    now_utc: datetime,
    quote_fresh_seconds: int,
    quote_aging_seconds: int,
    instrument_master_max_age_hours: int,
    broker_mapping_max_age_hours: int,
    data_mode: str,
) -> Dict[str, Any]:
    quote_dt = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
    import_dt = datetime.fromisoformat(import_timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
    quote_age_seconds = max((now_utc - quote_dt).total_seconds(), 0.0)
    import_age_hours = max((now_utc - import_dt).total_seconds() / 3600, 0.0)
    if not timestamp_utc:
        return {"state": "NOT_READY", "quote_age_seconds": None, "import_age_hours": import_age_hours, "mapping_age_hours": mapping_age_hours}
    if quote_age_seconds <= quote_fresh_seconds:
        state = "FRESH"
    elif quote_age_seconds <= quote_aging_seconds:
        state = "AGING"
    elif quote_age_seconds <= max(quote_aging_seconds, quote_fresh_seconds) * 4:
        state = "STALE"
    else:
        state = "EXPIRED"
    if import_age_hours > instrument_master_max_age_hours or mapping_age_hours > broker_mapping_max_age_hours:
        state = "STALE" if state in {"FRESH", "AGING"} else state
    if data_mode == "NOT_READY":
        state = "NOT_READY"
    return {
        "state": state,
        "quote_age_seconds": round(quote_age_seconds, 2),
        "import_age_hours": round(import_age_hours, 2),
        "mapping_age_hours": round(mapping_age_hours, 2),
    }
