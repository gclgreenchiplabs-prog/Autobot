import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.heartbeat import HeartbeatMonitor
from app.settings import Settings


def test_market_data_heartbeat_degrades_when_tick_is_old():
    monitor = HeartbeatMonitor(Settings())
    monitor.record_valid_tick("2000-01-01T00:00:00+00:00")
    state = monitor.state(active_subscription_count=1, stale_instrument_count=0)

    assert state == "FAILED"
