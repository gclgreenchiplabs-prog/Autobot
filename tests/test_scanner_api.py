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
            database_path=str(tmp_path / "scanner_api.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    return TestClient(create_app(container))


def test_scanner_api_endpoints_return_ranked_payloads(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        summary = client.get("/api/scanner/summary").json()
        intraday = client.get("/api/scanner/intraday").json()
        btst = client.get("/api/scanner/btst").json()
        swing = client.get("/api/scanner/swing").json()
        portfolio = client.get("/api/scanner/portfolio").json()
        options = client.get("/api/scanner/options").json()
        watchlist = client.get("/api/scanner/watchlist").json()
        avoid = client.get("/api/scanner/avoid").json()
        regime = client.get("/api/scanner/regime").json()
        manual_scan = client.post("/api/control/scan").json()

    assert summary["market_regime"]
    assert intraday
    assert btst
    assert swing
    assert portfolio
    assert isinstance(options, list)
    assert isinstance(watchlist, list)
    assert isinstance(avoid, list)
    assert regime["regime"]
    assert manual_scan["scanner"]["market_regime"]


def test_scanner_candidate_api_includes_enriched_fields(tmp_path: Path) -> None:
    with build_client(tmp_path) as client:
        candidates = client.get("/api/scanner/candidates").json()

    assert candidates
    first = candidates[0]
    assert "candidate_bucket" in first
    assert "decision" in first
    assert "risk_level" in first
    assert "payload_json" in first
    assert "scores" in first["payload_json"]
