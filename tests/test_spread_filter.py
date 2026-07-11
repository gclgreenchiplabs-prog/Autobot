import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.spread import evaluate_spread


def test_spread_pass_warn_fail_and_missing_fields():
    assert evaluate_spread({"bid": 100.0, "ask": 100.2}, 0.50, "FRESH")["state"] == "PASS"
    assert evaluate_spread({"bid": 100.0, "ask": 100.8}, 1.00, "FRESH")["state"] == "WARN"
    assert evaluate_spread({"bid": 100.0, "ask": 102.0}, 0.50, "FRESH")["state"] == "FAIL"
    assert evaluate_spread({"bid": None, "ask": 102.0}, 0.50, "FRESH")["state"] == "NOT_READY"
    assert evaluate_spread({"bid": 103.0, "ask": 102.0}, 0.50, "FRESH")["state"] == "FAIL"
    assert evaluate_spread({"bid": 100.0, "ask": 100.2}, 0.50, "STALE")["state"] == "FAIL"
