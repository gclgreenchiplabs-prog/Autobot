import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.settings import Settings


def test_market_data_dashboard_sections_render(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "market_data_dashboard.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="FIXTURE",
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})

    with TestClient(create_app(container)) as client:
        html = client.get("/").text
        state = client.get("/api/dashboard-state").json()

    assert "Market Data Status" in html
    assert "Audit Timeline" in html
    assert "market_data_status" in state
    assert "audit_timeline" in state
