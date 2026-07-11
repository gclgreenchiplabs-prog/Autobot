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
            database_path=str(tmp_path / "instrument_api.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    return TestClient(create_app(container))


def test_instrument_api_filters_pagination_and_import(tmp_path):
    with build_client(tmp_path) as client:
        companies = client.get("/api/companies", params={"limit": 3, "offset": 0}).json()
        instruments = client.get("/api/instruments", params={"exchange": "NSE", "limit": 5, "offset": 0}).json()
        fno = client.get("/api/universe/fno").json()
        quality = client.get("/api/market-data/quality", params={"quality_class": "FAILED"}).json()
        stale = client.get("/api/market-data/stale").json()
        liquidity = client.get("/api/market-data/liquidity", params={"liquidity_class": "ILLIQUID"}).json()
        candidates = client.get("/api/scanner/candidates").json()
        import_result = client.post("/api/control/import-instruments", json={"source": "FIXTURE"}).json()

    assert len(companies) == 3
    assert all(item["exchange"] == "NSE" for item in instruments)
    assert fno
    assert quality
    assert stale
    assert liquidity
    assert candidates
    assert import_result["validation_status"] == "SUCCESS"
