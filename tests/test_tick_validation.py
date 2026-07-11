import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.market_data.tick_validator import TickValidator
from app.settings import Settings


def test_tick_validator_rejects_invalid_price_and_crossed_market(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "tick_validation.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    mapping = next(
        item
        for item in container.instrument_repository.list_mappings()
        if item["broker"] == "fyers" and item["mapping_status"] in {"READY", "PARTIAL"}
    )
    instrument = container.instrument_repository.get_instrument(mapping["instrument_id"])
    validator = TickValidator(container.settings, container.instrument_repository)
    tick = {
        "tick_id": "bad-tick",
        "instrument_id": instrument["instrument_id"],
        "company_id": instrument["company_id"],
        "exchange": instrument["exchange"],
        "segment": instrument["segment"],
        "symbol": instrument["symbol"],
        "source": "fyers",
        "data_mode": "FIXTURE",
        "timestamp_exchange": "2026-07-12T03:45:01+00:00",
        "timestamp_received": "2026-07-12T03:45:01+00:00",
        "timestamp_utc": "2026-07-12T03:45:01+00:00",
        "bid": 105.0,
        "ask": 100.0,
        "ltp": -1.0,
        "volume": 10,
        "raw_reference": {},
    }

    result = validator.validate(tick)

    assert result["state"] == "REJECTED"
