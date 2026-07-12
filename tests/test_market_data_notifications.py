import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.settings import Settings


def test_market_data_events_persist_notifications_and_timeline(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "market_data_notifications.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="FIXTURE",
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    container.notification_service.start()
    service = container.market_data_service
    service.start_fixture()
    instrument_id = container.instrument_repository.list_instruments(limit=1, offset=0)[0]["instrument_id"]
    service.subscribe(instrument_ids=[instrument_id], consumer="notify")
    service.detect_feed_health()

    notifications = container.notification_service.list_notifications(limit=50)
    timeline = container.audit_repository.list_entries(limit=50)

    assert any(item["notification_type"].startswith("MARKET_DATA_") or item["notification_type"] == "CANDLE_COMPLETED" for item in notifications)
    assert any(entry["module"] == "market-data" for entry in timeline)
