import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.settings import Settings


def test_scanner_dashboard_sections_and_state_render(tmp_path: Path) -> None:
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "scanner_dashboard.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})

    with TestClient(create_app(container)) as client:
        html = client.get("/").text
        state = client.get("/api/dashboard-state").json()

    assert "Scanner Summary" in html
    assert "Market Regime" in html
    assert "Top 20 Stocks" in html
    assert "Avoid List" in html
    assert state["scanner_summary"]["market_regime"]
    assert "scanner_intraday" in state
    assert "scanner_watchlist" in state
    assert "scanner_sector_rotation" in state
