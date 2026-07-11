from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BrokerConnection:
    name: str
    connected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "connected": self.connected, "metadata": self.metadata}


@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    action: str
    price: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "action": self.action,
            "price": self.price,
        }
