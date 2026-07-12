import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.settings import Settings


def build_container(tmp_path: Path) -> AppContainer:
    return AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "market_data_service.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="FIXTURE",
        )
    )


def test_market_data_service_subscribe_updates_quote_cache_and_candles(tmp_path):
    container = build_container(tmp_path)
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    service = container.market_data_service
    service.start()
    service.start_fixture()

    instrument_id = container.instrument_repository.list_instruments(limit=1, offset=0)[0]["instrument_id"]
    result = service.subscribe(instrument_ids=[instrument_id], consumer="test", timeframes=["1m", "5m"])

    assert result["source"] == "fixture"
    assert service.quotes(instrument_id=instrument_id)["data_mode"] == "FIXTURE"

    for _ in range(5):
        service.process_adapter_ticks("fixture")

    assert service.status()["quote_cache_size"] >= 1
    assert service.repository.list_candles(limit=20)
