from __future__ import annotations

from typing import Any, Dict

from app.brokers.base import BaseBroker
from app.models import BrokerConnection, OrderRequest


class DhanAdapter(BaseBroker):
    name = "dhan"
    is_paper = False

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self.connection = BrokerConnection(name=self.name, connected=bool(settings.api_key), metadata={"mode": "live"})

    def connect(self) -> BrokerConnection:
        self.connection.connected = bool(self.settings.api_key)
        return self.connection

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        return {
            "status": "submitted",
            "broker": self.name,
            "symbol": order.symbol,
            "quantity": order.quantity,
            "action": order.action,
            "price": order.price,
        }
