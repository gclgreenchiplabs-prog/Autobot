from __future__ import annotations

from typing import Any, Dict, Optional

from app.brokers.base import BaseBroker
from app.brokers.dhan.adapter import DhanAdapter
from app.brokers.fyers.adapter import FyersAdapter
from app.brokers.paper.adapter import PaperAdapter
from app.brokers.idempotency import IdempotencyStore
from app.brokers.reconciliation import ReconciliationState
from app.models import OrderRequest
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

    def place_order(
        self,
        order: OrderRequest,
        idempotency_key: Optional[str] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        reconciliation_state: Optional[ReconciliationState] = None,
        timeout: bool = False,
    ) -> Dict[str, Any]:
        store = idempotency_store or IdempotencyStore()
        reconciliation = reconciliation_state or ReconciliationState()

        if idempotency_key:
            existing = store.get(idempotency_key)
            if existing is not None:
                return existing["result"]

        broker = self.create_broker()
        if timeout:
            reconciliation.mark_timeout(reason="request-timeout")
            result = {
                "status": "BROKER_RECONCILIATION",
                "broker": broker.name,
                "order": order.as_dict(),
                "mode": "paper" if self.settings.is_paper_mode else "live",
                "reconciliation": reconciliation.as_dict(),
            }
        else:
            result = broker.place_order(order)
            result = {
                **result,
                "broker": broker.name,
                "mode": "paper" if self.settings.is_paper_mode else "live",
                "reconciliation": reconciliation.as_dict(),
            }

        if idempotency_key:
            store.save(idempotency_key, result)
        return result
