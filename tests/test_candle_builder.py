import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.candle_builder import CandleBuilder


def test_candle_builder_completes_1m_and_5m_buckets():
    builder = CandleBuilder(enabled_timeframes=["1m", "5m"])
    tick_one = {
        "instrument_id": "NSE:CASH:ABC",
        "source": "fixture",
        "data_mode": "FIXTURE",
        "timestamp_utc": "2026-07-12T03:45:00+00:00",
        "ltp": 100.0,
        "volume": 100,
        "traded_value": 10000.0,
        "vwap": 100.0,
        "open_interest": 1000.0,
    }
    tick_two = {**tick_one, "timestamp_utc": "2026-07-12T03:46:00+00:00", "ltp": 101.0, "volume": 150, "traded_value": 15150.0}

    completed = builder.ingest(tick_one)
    completed += builder.ingest(tick_two)

    assert any(item["timeframe"] == "1m" for item in completed)
    assert builder.current_candles()
