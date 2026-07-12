import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.sequence import SequenceTracker


def test_sequence_tracker_detects_duplicate_gap_and_out_of_order():
    tracker = SequenceTracker()
    base = {"source": "fixture", "instrument_id": "NSE:CASH:ABC", "timestamp_utc": "2026-07-12T03:45:00+00:00"}

    first = tracker.evaluate({**base, "sequence_number": 1}, fingerprint="a")
    duplicate = tracker.evaluate({**base, "sequence_number": 1}, fingerprint="a")
    gap = tracker.evaluate({**base, "sequence_number": 3}, fingerprint="b")
    out_of_order = tracker.evaluate({**base, "sequence_number": 2}, fingerprint="c")

    assert first["state"] == "VALID"
    assert duplicate["state"] == "DUPLICATE"
    assert gap["state"] == "WARNING"
    assert out_of_order["state"] == "OUT_OF_ORDER"
