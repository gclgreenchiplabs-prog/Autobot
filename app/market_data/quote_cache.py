from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional


class LatestQuoteCache:
    def __init__(self) -> None:
        self._quotes: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()

    def update(self, tick: Dict[str, Any]) -> bool:
        instrument_id = tick["instrument_id"]
        with self._lock:
            existing = self._quotes.get(instrument_id)
            if existing is not None:
                existing_dt = datetime.fromisoformat(existing["timestamp_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
                incoming_dt = datetime.fromisoformat(tick["timestamp_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
                if incoming_dt < existing_dt:
                    return False
                if incoming_dt == existing_dt and (tick.get("sequence_number") or -1) < (existing.get("sequence_number") or -1):
                    return False
            self._quotes[instrument_id] = dict(tick)
            return True

    def get(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            quote = self._quotes.get(instrument_id)
            return dict(quote) if quote is not None else None

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._quotes.values()]

    def size(self) -> int:
        with self._lock:
            return len(self._quotes)

    def quote_age_seconds(self, instrument_id: str, now_utc: Optional[datetime] = None) -> Optional[float]:
        quote = self.get(instrument_id)
        if quote is None:
            return None
        base = now_utc or datetime.now(timezone.utc)
        quote_time = datetime.fromisoformat(quote["timestamp_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
        return (base - quote_time).total_seconds()
