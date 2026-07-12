import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.reconnect import ReconnectPolicy


def test_reconnect_policy_is_bounded_and_cancellable():
    policy = ReconnectPolicy(initial_seconds=2, max_seconds=10, max_attempts=3, jitter_fn=lambda attempt: 0.5)

    assert policy.next_delay() == 2.5
    assert policy.next_delay() == 4.5
    assert policy.next_delay() == 8.5
    assert policy.next_delay() is None
    policy.reset()
    policy.cancel()
    assert policy.next_delay() is None
