import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.settings import Settings


def build_client(tmp_path: Path) -> TestClient:
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "market_data_api.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="FIXTURE",
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    return TestClient(create_app(container))


def test_market_data_api_endpoints_and_controls(tmp_path):
    with build_client(tmp_path) as client:
        instruments = client.get("/api/instruments", params={"limit": 1}).json()
        instrument_id = instruments[0]["instrument_id"]
        assert client.post("/api/control/market-data/start-fixture").status_code == 200
        subscribe = client.post("/api/control/market-data/subscribe", json={"instrument_ids": [instrument_id], "consumer": "api"}).json()
        status = client.get("/api/market-data/status").json()
        quotes = client.get("/api/market-data/quotes").json()
        candles = client.get("/api/market-data/candles").json()
        heartbeat = client.get("/api/market-data/heartbeat").json()
        timeline = client.get("/api/audit/timeline").json()

    assert subscribe["source"] == "fixture"
    assert status["market_data_mode"] == "fixture"
    assert quotes
    assert heartbeat["state"] in {"HEALTHY", "DEGRADED", "NOT_READY", "STALE"}
    assert isinstance(candles, list)
    assert timeline


def test_market_data_control_validation_rejects_fixture_when_not_in_fixture_mode(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "market_data_api_live.db"),
            forced_test_mode=True,
            enable_notifications=False,
            market_data_mode="LIVE",
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    with TestClient(create_app(container)) as client:
        response = client.post("/api/control/market-data/start-fixture")
    assert response.status_code == 400
