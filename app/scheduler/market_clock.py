from __future__ import annotations

from datetime import datetime
from typing import Optional

import pytz

from app.settings import Settings


class MarketClock:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def current_ist(self) -> datetime:
        return datetime.now(pytz.timezone(self.settings.timezone))

    def current_session_state(self, now: Optional[datetime] = None) -> str:
        current = now or self.current_ist()
        if self.settings.forced_test_mode:
            return "FORCED_TEST"
        if current.weekday() >= 5:
            return "MARKET_CLOSED"
        hour = current.hour
        minute = current.minute
        current_minutes = hour * 60 + minute

        premarket = self._to_minutes(self.settings.premarket_start_time)
        open_time = self._to_minutes(self.settings.market_open_time)
        close_time = self._to_minutes(self.settings.market_close_time)
        post_market = self._to_minutes(self.settings.post_market_end_time)

        if premarket <= current_minutes < open_time:
            return "PREMARKET"
        if open_time <= current_minutes < close_time:
            return "MARKET_OPEN"
        if close_time <= current_minutes < post_market:
            return "POST_MARKET"
        return "MARKET_CLOSED"

    def _to_minutes(self, value: str) -> int:
        hour, minute = map(int, value.split(":"))
        return hour * 60 + minute
