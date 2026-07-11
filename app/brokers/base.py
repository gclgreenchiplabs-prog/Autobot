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

    def get_status(self) -> Dict[str, Any]:
        return {"name": self.name, "connected": True, "paper": self.is_paper}
