import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.brokers.router import BrokerRouter
from app.settings import Settings


def test_paper_broker_is_selected_by_default():
    router = BrokerRouter(Settings())
    broker = router.create_broker()

    assert broker.name == "paper"
    assert broker.is_paper is True
    assert broker.get_status()["connected"] is True
