import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.quote_cache import LatestQuoteCache


def test_quote_cache_keeps_newest_tick_only():
    cache = LatestQuoteCache()
    older = {"instrument_id": "A", "timestamp_utc": "2026-07-12T03:45:00+00:00", "sequence_number": 1}
    newer = {"instrument_id": "A", "timestamp_utc": "2026-07-12T03:45:01+00:00", "sequence_number": 2}

    assert cache.update(newer) is True
    assert cache.update(older) is False
    assert cache.get("A")["sequence_number"] == 2
