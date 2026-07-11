from __future__ import annotations

from typing import Any

from app.brokers.base import BaseBroker
from app.brokers.dhan.adapter import DhanAdapter
from app.brokers.fyers.adapter import FyersAdapter
from app.brokers.paper.adapter import PaperAdapter
from app.settings import Settings


class BrokerRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def create_broker(self) -> BaseBroker:
        mode = (self.settings.trading_mode or "paper").lower()
        if mode == "live":
            primary = (self.settings.primary_broker or "fyers").lower()
            if primary == "dhan":
                return DhanAdapter(self.settings)
            return FyersAdapter(self.settings)

        return PaperAdapter(self.settings)
