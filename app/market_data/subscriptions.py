from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Set


@dataclass
class SubscriptionRecord:
    subscription_id: str
    instrument_id: str
    source: str
    broker_symbol: str
    requested_at: str
    subscribed_at: Optional[str] = None
    status: str = "PENDING"
    consumer: str = "system"
    timeframes: List[str] = field(default_factory=list)
    last_tick_at: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    consumer_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SubscriptionRegistry:
    def __init__(self) -> None:
        self._records: Dict[tuple[str, str], SubscriptionRecord] = {}
        self._consumers: Dict[tuple[str, str], Set[str]] = {}
        self._timeframes: Dict[tuple[str, str], Set[str]] = {}
        self._lock = RLock()

    def subscribe(
        self,
        *,
        instrument_id: str,
        source: str,
        broker_symbol: str,
        consumer: str,
        timeframes: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        key = (source.lower(), instrument_id)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            consumers = self._consumers.setdefault(key, set())
            consumers.add(consumer)
            timeframe_set = self._timeframes.setdefault(key, set())
            timeframe_set.update(timeframes or [])
            record = self._records.get(key)
            if record is None:
                record = SubscriptionRecord(
                    subscription_id=f"{source.lower()}:{instrument_id}",
                    instrument_id=instrument_id,
                    source=source.lower(),
                    broker_symbol=broker_symbol,
                    requested_at=now,
                    consumer=consumer,
                    timeframes=sorted(timeframe_set),
                )
                self._records[key] = record
            else:
                record.status = "PENDING" if record.status == "UNSUBSCRIBED" else record.status
                record.timeframes = sorted(timeframe_set)
                record.consumer_count = len(consumers)
                record.consumer = consumer
            record.consumer_count = len(consumers)
            return record.to_dict()

    def mark_active(self, source: str, instrument_id: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            record.status = "ACTIVE"
            record.subscribed_at = datetime.now(timezone.utc).isoformat()
            return record.to_dict()

    def mark_failed(self, source: str, instrument_id: str, error: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            record.status = "FAILED"
            record.retry_count += 1
            record.last_error = error
            return record.to_dict()

    def mark_stale(self, source: str, instrument_id: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            record.status = "STALE"
            return record.to_dict()

    def unsubscribe(self, *, instrument_id: str, source: str, consumer: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            consumers = self._consumers.get(key, set())
            consumers.discard(consumer)
            record = self._records.get(key)
            if record is None:
                return None
            if consumers:
                record.consumer_count = len(consumers)
                return record.to_dict()
            record.status = "UNSUBSCRIBED"
            record.consumer_count = 0
            return record.to_dict()

    def touch_tick(self, source: str, instrument_id: str, timestamp_utc: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            record.last_tick_at = timestamp_utc
            if record.status in {"PENDING", "STALE", "RETRYING"}:
                record.status = "ACTIVE"
            return record.to_dict()

    def retrying(self, source: str, instrument_id: str, error: str) -> Optional[Dict[str, Any]]:
        key = (source.lower(), instrument_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            record.status = "RETRYING"
            record.retry_count += 1
            record.last_error = error
            return record.to_dict()

    def list_records(self, *, source: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
        if source:
            records = [record for record in records if record.source == source.lower()]
        return [record.to_dict() for record in records]

    def active_count(self, *, source: Optional[str] = None) -> int:
        return sum(1 for record in self.list_records(source=source) if record["status"] == "ACTIVE")

    def subscription_count(self) -> int:
        return len(self.list_records())

    def resubscribe_snapshot(self, source: str) -> List[Dict[str, Any]]:
        records = []
        with self._lock:
            for key, record in self._records.items():
                if key[0] != source.lower():
                    continue
                if record.status != "UNSUBSCRIBED":
                    record.status = "PENDING"
                    records.append(record.to_dict())
        return records
