from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


TIMEFRAME_MINUTES = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1d": 60 * 24,
}


@dataclass
class CandleRecord:
    instrument_id: str
    source: str
    timeframe: str
    start_time: str
    end_time: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    traded_value: float
    vwap: float
    open_interest: float
    tick_count: int
    complete: bool
    data_mode: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CandleBuilder:
    def __init__(self, timezone_name: str = "Asia/Kolkata", enabled_timeframes: Optional[List[str]] = None) -> None:
        self.timezone_name = timezone_name
        self.enabled_timeframes = enabled_timeframes or ["1m", "5m", "15m", "30m", "1d"]
        self._current: Dict[tuple[str, str, str], CandleRecord] = {}
        self._completed: List[Dict[str, Any]] = []
        self._lock = RLock()

    def ingest(self, tick: Dict[str, Any]) -> List[Dict[str, Any]]:
        completed: List[Dict[str, Any]] = []
        price = float(tick.get("ltp") or 0.0)
        volume = int(tick.get("volume") or 0)
        traded_value = float(tick.get("traded_value") or price * max(volume, 0))
        oi = float(tick.get("open_interest") or 0.0)
        for timeframe in self.enabled_timeframes:
            start_dt, end_dt = self._bucket_bounds(tick["timestamp_utc"], timeframe)
            key = (tick["instrument_id"], tick["source"], timeframe)
            with self._lock:
                existing = self._current.get(key)
                if existing is not None and start_dt.isoformat() < existing.start_time:
                    continue
                if existing is not None and start_dt.isoformat() > existing.start_time:
                    existing.complete = True
                    completed.append(existing.to_dict())
                    self._completed.append(existing.to_dict())
                    existing = None
                if existing is None:
                    self._current[key] = CandleRecord(
                        instrument_id=tick["instrument_id"],
                        source=tick["source"],
                        timeframe=timeframe,
                        start_time=start_dt.isoformat(),
                        end_time=end_dt.isoformat(),
                        open=price,
                        high=price,
                        low=price,
                        close=price,
                        volume=volume,
                        traded_value=traded_value,
                        vwap=float(tick.get("vwap") or price),
                        open_interest=oi,
                        tick_count=1,
                        complete=False,
                        data_mode=tick["data_mode"],
                    )
                else:
                    if price == existing.close and tick["timestamp_utc"] == existing.end_time:
                        continue
                    existing.high = max(existing.high, price)
                    existing.low = min(existing.low, price)
                    existing.close = price
                    existing.volume = max(existing.volume, volume)
                    existing.traded_value = max(existing.traded_value, traded_value)
                    existing.vwap = float(tick.get("vwap") or existing.vwap)
                    existing.open_interest = oi
                    existing.tick_count += 1
        return completed

    def current_candles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [record.to_dict() for record in self._current.values()]

    def completed_candles(self, *, instrument_id: Optional[str] = None, timeframe: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            rows = list(self._completed)
        if instrument_id:
            rows = [row for row in rows if row["instrument_id"] == instrument_id]
        if timeframe:
            rows = [row for row in rows if row["timeframe"] == timeframe]
        return rows

    def _bucket_bounds(self, timestamp_utc: str, timeframe: str) -> tuple[datetime, datetime]:
        dt_utc = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        ist = dt_utc.astimezone(ZoneInfo(self.timezone_name))
        if timeframe == "1d":
            start_ist = ist.replace(hour=0, minute=0, second=0, microsecond=0)
            end_ist = start_ist + timedelta(days=1)
            return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)
        minutes = TIMEFRAME_MINUTES[timeframe]
        floored_minute = (ist.minute // minutes) * minutes
        start_ist = ist.replace(minute=floored_minute, second=0, microsecond=0)
        end_ist = start_ist + timedelta(minutes=minutes)
        return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)
