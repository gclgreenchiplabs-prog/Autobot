import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.brokers.reconciliation import ReconciliationState
from app.brokers.router import BrokerRouter
from app.models import OrderRequest
from app.settings import Settings


def test_timeout_marks_reconciliation_state():
    router = BrokerRouter(Settings())
    order = OrderRequest(symbol='BANKNIFTY', quantity=1, action='buy')

    result = router.place_order(order, idempotency_key='timeout-key', reconciliation_state=ReconciliationState(), timeout=True)

    assert result['status'] == 'BROKER_RECONCILIATION'
    assert result['reconciliation']['status'] == 'BROKER_RECONCILIATION'
