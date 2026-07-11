from __future__ import annotations

from typing import Any, Dict

from app.brokers.base import BaseBroker
from app.models import BrokerConnection, OrderRequest


class PaperAdapter(BaseBroker):
    name = "paper"
    is_paper = True

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self.connection = BrokerConnection(name=self.name, connected=True, metadata={"mode": "paper"})

    def connect(self) -> BrokerConnection:
        self.connection.connected = True
        return self.connection

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        return {
            "status": "paper",
            "symbol": order.symbol,
            "quantity": order.quantity,
            "action": order.action,
            "price": order.price,
        }
