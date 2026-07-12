import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.settings import Settings


def test_fixture_market_data_is_always_labeled_fixture(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "fixture_market_data.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="FIXTURE",
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    service = container.market_data_service
    service.start_fixture()
    instrument_id = container.instrument_repository.list_instruments(limit=1, offset=0)[0]["instrument_id"]
    service.subscribe(instrument_ids=[instrument_id], consumer="fixture-test")
    quote = service.quotes(instrument_id=instrument_id)

    assert quote["data_mode"] == "FIXTURE"
    assert service.connect("fixture")["data_state"] == "FIXTURE"
