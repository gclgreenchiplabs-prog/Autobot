import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.subscriptions import SubscriptionRegistry


def test_subscription_registry_reference_counts_and_deduplicates():
    registry = SubscriptionRegistry()
    first = registry.subscribe(instrument_id="A", source="fixture", broker_symbol="A-EQ", consumer="dash", timeframes=["1m"])
    second = registry.subscribe(instrument_id="A", source="fixture", broker_symbol="A-EQ", consumer="api", timeframes=["5m"])

    assert first["subscription_id"] == second["subscription_id"]
    assert second["consumer_count"] == 2
    registry.unsubscribe(instrument_id="A", source="fixture", consumer="dash")
    final = registry.unsubscribe(instrument_id="A", source="fixture", consumer="api")
    assert final["status"] == "UNSUBSCRIBED"
