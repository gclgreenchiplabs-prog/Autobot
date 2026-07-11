import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.quality import evaluate_quality


def test_data_quality_scoring_and_conflicts():
    good = evaluate_quality(
        instrument={"symbol": "RELIANCE", "exchange": "NSE", "segment": "CASH", "instrument_type": "EQUITY", "isin": "INE002A01018", "trading_symbol": "RELIANCE"},
        quote={"ltp": 2500.0, "high": 2510.0, "low": 2480.0, "volume": 100000},
        mapping_rows=[{"mapping_status": "READY"}],
        spread={"state": "PASS", "reasons": []},
        staleness={"state": "FRESH"},
        has_conflict=False,
        now_utc=datetime.now(timezone.utc),
    )
    bad = evaluate_quality(
        instrument={"symbol": "SHARED", "exchange": "BSE", "segment": "CASH", "instrument_type": "EQUITY", "isin": "INEBAD", "trading_symbol": "SHARED"},
        quote={"ltp": 0.0, "high": 100.0, "low": 120.0, "volume": -1},
        mapping_rows=[{"mapping_status": "CONFLICT"}],
        spread={"state": "FAIL", "reasons": ["Spread too wide"]},
        staleness={"state": "EXPIRED"},
        has_conflict=True,
        now_utc=datetime.now(timezone.utc),
    )
    assert good["quality_class"] in {"CONFIRMED", "PARTIAL"}
    assert bad["quality_class"] == "FAILED"
