from __future__ import annotations

from typing import Any, Dict

from app.brokers.base import BaseBroker
from app.brokers.readiness import BrokerCapabilityEvaluator
from app.models import BrokerConnection, OrderRequest


class FyersAdapter(BaseBroker):
    name = "fyers"
    is_paper = False

    def __init__(self, settings: Any) -> None:
        super().__init__(settings)
        self.connection = BrokerConnection(name=self.name, connected=False, metadata={"mode": "live"})

    def connect(self) -> BrokerConnection:
        self.connection.connected = False
        self.connection.metadata = {"mode": "live", "reason": "Live FYERS execution is not activated by configuration alone."}
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

    def configuration_readiness(self) -> Dict[str, Any]:
        return self._evaluator().configuration_readiness().to_dict()

    def authentication_readiness(self) -> Dict[str, Any]:
        return self._evaluator().authentication_readiness().to_dict()

    def market_data_readiness(self) -> Dict[str, Any]:
        return self._evaluator().market_data_readiness().to_dict()

    def option_chain_readiness(self) -> Dict[str, Any]:
        return self._evaluator().option_chain_readiness().to_dict()

    def execution_readiness(self) -> Dict[str, Any]:
        return self._evaluator().execution_readiness().to_dict()

    def health_snapshot(self) -> Dict[str, Any]:
        return self._evaluator().health_snapshot()

    def _evaluator(self) -> BrokerCapabilityEvaluator:
        return BrokerCapabilityEvaluator(
            settings=self.settings,
            broker=self.name,
            sdk_available=True,
            authenticated=False,
            connected=False,
        )
