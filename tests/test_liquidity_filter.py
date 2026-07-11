import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.liquidity import evaluate_liquidity


def test_liquidity_scoring_high_and_illiquid():
    high = evaluate_liquidity(
        {"traded_value": 20_000_000.0, "volume": 100000, "bid_quantity": 10000, "ask_quantity": 12000, "bid": 100.0, "ask": 100.2, "open_interest": 2000},
        "FRESH",
        min_intraday_traded_value=10_000_000.0,
        min_btst_traded_value=5_000_000.0,
        min_swing_traded_value=1_000_000.0,
        min_option_oi=1000,
        min_option_volume=100,
        max_allowed_spread_pct=0.50,
        instrument_type="EQUITY",
        fno_eligible=False,
    )
    low = evaluate_liquidity(
        {"traded_value": 20_000.0, "volume": 0, "bid_quantity": 10, "ask_quantity": 5, "bid": 75.0, "ask": 81.5, "open_interest": 0},
        "STALE",
        min_intraday_traded_value=10_000_000.0,
        min_btst_traded_value=5_000_000.0,
        min_swing_traded_value=1_000_000.0,
        min_option_oi=1000,
        min_option_volume=100,
        max_allowed_spread_pct=0.50,
        instrument_type="EQUITY",
        fno_eligible=False,
    )
    assert high["liquidity_class"] in {"HIGH", "MEDIUM"}
    assert high["eligible_for_intraday"] is True
    assert low["liquidity_class"] == "ILLIQUID"
    assert low["eligible_for_intraday"] is False
