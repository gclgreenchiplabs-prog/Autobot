import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.brokers.idempotency import IdempotencyStore
from app.brokers.reconciliation import ReconciliationState
from app.brokers.router import BrokerRouter
from app.models import OrderRequest
from app.settings import Settings


def test_same_idempotency_key_does_not_create_two_orders():
    store = IdempotencyStore()
    router = BrokerRouter(Settings())
    order = OrderRequest(symbol='NIFTY', quantity=1, action='buy')

    first = router.place_order(order, idempotency_key='same-key', idempotency_store=store, reconciliation_state=ReconciliationState())
    second = router.place_order(order, idempotency_key='same-key', idempotency_store=store, reconciliation_state=ReconciliationState())

    assert first == second
