import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.brokers.dhan.market_data import DhanMarketDataAdapter
from app.brokers.fyers.market_data import FyersMarketDataAdapter
from app.market_data.adapters.fixture import FixtureMarketDataAdapter
from app.settings import Settings


def test_market_data_adapters_expose_readiness_states():
    settings = Settings(
        fyers_market_data_enable=False,
        dhan_market_data_enable=False,
    )

    fyers = FyersMarketDataAdapter(settings)
    dhan = DhanMarketDataAdapter(settings)
    fixture = FixtureMarketDataAdapter()

    assert fyers.readiness()["state"] in {"NOT_CONFIGURED", "SDK_NOT_INSTALLED"}
    assert dhan.readiness()["state"] == "NOT_CONFIGURED"
    assert fixture.readiness()["state"] == "DISCONNECTED"
