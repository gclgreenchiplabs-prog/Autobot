import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.settings import Settings


def build_container(tmp_path: Path) -> AppContainer:
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "scanner_engine.db"),
            forced_test_mode=True,
            enable_notifications=False,
        )
    )
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    return container


def test_scanner_engine_produces_ranked_candidates_and_summary(tmp_path: Path) -> None:
    container = build_container(tmp_path)
    state = container.scanner_engine.refresh(reason="test")

    assert state["summary"]["intraday_count"] > 0
    assert state["summary"]["market_regime"]
    assert state["intraday"]

    top = state["intraday"][0]
    assert 0.0 <= float(top["score"]) <= 100.0
    assert 0.0 <= float(top["confidence"]) <= 100.0
    assert top["payload_json"]["entry"] > 0
    assert top["payload_json"]["atr"] >= 0
    assert top["payload_json"]["scores"]["final_score"] == top["score"]
    assert top["payload_json"]["scores"]["ai_confidence"] == top["confidence"]


def test_scanner_framework_risk_from_corporate_events_and_news(tmp_path: Path) -> None:
    container = build_container(tmp_path)
    container.state_store.set(
        "scanner_corporate_events",
        {
            "RELIANCE": [
                {"event_type": "RESULTS", "impact": "HIGH_RISK", "severity": "WARNING", "reason": "Framework earnings risk"}
            ]
        },
    )
    container.state_store.set(
        "scanner_news_sentiment",
        {
            "RELIANCE": {"sentiment": "NEGATIVE", "reason": "Framework negative sentiment"}
        },
    )

    state = container.scanner_engine.refresh(reason="test-framework")
    reliance_avoid = [item for item in state["avoid"] if item["symbol"] == "RELIANCE"]
    corporate_watch = [item for item in state["corporate_events"] if item["symbol"] == "RELIANCE"]

    assert corporate_watch
    assert reliance_avoid
    assert any(item["decision"] in {"AVOID", "NO TRADE"} for item in reliance_avoid)
    assert any(item["payload_json"]["news"]["label"] == "NEGATIVE" for item in reliance_avoid)


def test_scanner_market_regime_and_sector_rotation_are_populated(tmp_path: Path) -> None:
    container = build_container(tmp_path)
    state = container.scanner_engine.refresh(reason="test-regime")

    assert state["regime"]["regime"] in {
        "TRENDING_BULL",
        "TRENDING_BEAR",
        "RANGE",
        "VOLATILE",
        "LOW_LIQUIDITY",
        "GAP_UP",
        "GAP_DOWN",
        "EVENT_DRIVEN",
    }
    assert state["regime"]["reasons"]
    assert state["sector_rotation"]
    assert state["risk_heatmap"]
