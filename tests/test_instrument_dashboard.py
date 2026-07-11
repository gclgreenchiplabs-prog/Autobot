import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.settings import Settings


def test_dashboard_renders_universe_sections(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "dashboard_universe.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    with TestClient(create_app(container)) as client:
        response = client.get("/")
        state = client.get("/api/dashboard-state").json()

    assert response.status_code == 200
    assert "Universe Summary" in response.text
    assert "Import Instruments" in response.text
    assert state["universe_summary"]["total_companies"] == 7
    assert state["instrument_table"]
    assert "broker_mapping_summary" in state
