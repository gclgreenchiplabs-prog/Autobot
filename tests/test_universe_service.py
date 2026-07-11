import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.settings import Settings


def build_container(tmp_path: Path) -> AppContainer:
    return AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "universe.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )


def test_company_deduplication_preferred_exchange_and_fno_counts(tmp_path):
    container = build_container(tmp_path)
    result = container.instrument_service.import_instruments({"source": "FIXTURE"})
    status = container.instrument_service.universe_status()
    companies = container.instrument_service.list_companies(limit=100, offset=0)
    zen = next(item for item in companies if item["company_name"] == "Zen Energy Limited")
    assert result["validation_status"] == "SUCCESS"
    assert status["total_companies"] == 7
    assert status["fno_count"] == 4
    assert zen["preferred_exchange"] == "BSE"


def test_conflicts_and_notification_persistence_from_import(tmp_path):
    container = build_container(tmp_path)
    container.notification_service.start()
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    conflicts = container.instrument_service.repository.list_conflicts()
    notifications = container.notification_service.list_notifications(notification_type="INSTRUMENT_IMPORT_COMPLETED")
    assert len(conflicts) >= 2
    assert any(conflict["conflict_type"] == "SYMBOL_ISIN_CONFLICT" for conflict in conflicts)
    assert notifications


def test_cache_initialization_and_failed_import_rollback(tmp_path):
    container = build_container(tmp_path)
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    before = container.instrument_service.universe_status()["total_instruments"]
    bad_file = tmp_path / "bad_import.json"
    bad_file.write_text(json.dumps({"source": "MANUAL_IMPORT", "source_version": "broken"}), encoding="utf-8")

    with pytest.raises(Exception):
        container.instrument_service.import_instruments({"source": "MANUAL_IMPORT", "path": str(bad_file)})

    after = container.instrument_service.universe_status()["total_instruments"]
    assert before == after
    assert container.instrument_service.repository.latest_import_run()["validation_status"] in {"SUCCESS", "FAILED"}
