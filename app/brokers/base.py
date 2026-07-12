from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models import BrokerConnection, OrderRequest


class BaseBroker(ABC):
    name: str = "base"
    is_paper: bool = False

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    @abstractmethod
    def connect(self) -> BrokerConnection:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        raise NotImplementedError

    def configuration_readiness(self) -> Dict[str, Any]:
        return self.health_snapshot()

    def authentication_readiness(self) -> Dict[str, Any]:
        return self.health_snapshot()

    def market_data_readiness(self) -> Dict[str, Any]:
        return self.health_snapshot()

    def option_chain_readiness(self) -> Dict[str, Any]:
        return self.health_snapshot()

    def execution_readiness(self) -> Dict[str, Any]:
        return self.health_snapshot()

    def health_snapshot(self) -> Dict[str, Any]:
        return {
            "broker": self.name,
            "configured": False,
            "enabled": False,
            "credentials_present": False,
            "sdk_available": True,
            "authenticated": False,
            "connected": False,
            "market_data_ready": False,
            "option_chain_ready": False,
            "execution_ready": False,
            "active": self.is_paper,
            "status": "NOT_CONFIGURED",
            "reason": "No broker readiness implementation available.",
            "last_error": None,
            "last_checked_at": "",
        }

    def get_status(self) -> Dict[str, Any]:
        return {"name": self.name, "connected": self.connect().connected, "paper": self.is_paper, "readiness": self.health_snapshot()}
