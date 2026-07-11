import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.application import create_app
from app.container import AppContainer
from app.notifications.models import NotificationType
from app.settings import Settings


def build_container(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "telemetry.db"),
            forced_test_mode=True,
        )
    )
    container.repository.initialize_schema()
    container.migrations.apply()
    container.wire_runtime()
    container.state_store.set(
        "positions",
        [
            {
                "trade_id": "trade-open-1",
                "symbol": "RELIANCE",
                "underlying": "RELIANCE",
                "exchange": "NSE",
                "instrument_type": "OPTION",
                "option_type": "CE",
                "strike": 3000,
                "expiry": "30-Jul-2026",
                "side": "BUY",
                "quantity": 500,
                "lots": 2,
                "entry_price": 41.60,
                "current_price": 54.20,
                "highest_price": 57.10,
                "highest_profit": 7750.0,
                "current_stop": 49.80,
                "initial_stop": 36.80,
                "t1": 48.50,
                "t2": 56.00,
                "t3": 67.50,
                "next_predicted_target": 56.00,
                "t1_status": "HIT",
                "t2_status": "PENDING",
                "t3_status": "PENDING",
                "capital_used_trade": 20800.0,
                "hold_reason": "Momentum remains above VWAP and volume is supportive.",
                "exit_condition": "5-minute close below trailing stop.",
                "entry_timestamp": "2026-07-11T09:42:18+05:30",
                "position_status": "OPEN",
            }
        ],
    )
    container.state_store.set(
        "closed_trades",
        [
            {
                "trade_id": "trade-closed-1",
                "symbol": "TCS",
                "exchange": "NSE",
                "instrument_type": "OPTION",
                "option_type": "PE",
                "strike": 4000,
                "expiry": "30-Jul-2026",
                "side": "BUY",
                "quantity": 300,
                "lots": 1,
                "entry_price": 32.0,
                "exit_price": 40.0,
                "capital_used_trade": 9600.0,
                "capital_released": 12000.0,
                "highest_price": 42.0,
                "highest_profit": 3000.0,
                "mfe": 3000.0,
                "mae": -600.0,
                "entry_timestamp": "2026-07-11T10:00:00+05:30",
                "exit_timestamp": "2026-07-11T11:00:00+05:30",
                "exit_reason": "Target hit",
                "net_pnl": 2200.0,
                "status": "CLOSED",
            }
        ],
    )
    container.state_store.set("account", {"opening_capital": 500000.0, "capital_reserved": 5000.0})
    return container


def test_account_snapshot_consistency_and_capital_fields(tmp_path):
    container = build_container(tmp_path)
    account = container.telemetry_service.build_account_snapshot(reason="test").to_dict()
    assert account["realized_pnl"] == 2200.0
    assert account["unrealized_pnl"] == 6300.0
    assert account["capital_used_day"] == 20800.0
    assert account["capital_available"] == 482700.0
    assert account["account_equity"] == 508500.0


def test_position_and_trade_snapshots(tmp_path):
    container = build_container(tmp_path)
    positions = [snapshot.to_dict() for snapshot in container.telemetry_service.build_position_snapshots()]
    trades = [snapshot.to_dict() for snapshot in container.telemetry_service.build_trade_snapshots()]
    assert positions[0]["current_pnl"] == 6300.0
    assert positions[0]["locked_profit"] == 4100.0
    assert any(trade["status"] == "CLOSED" and trade["capital_released"] == 12000.0 for trade in trades)


def test_api_filtering_and_dashboard_sections(tmp_path):
    container = build_container(tmp_path)
    container.notification_service.start()
    container.notification_service.create_notification(
        NotificationType.SIGNAL_GENERATED.value,
        {
            "symbol": "RELIANCE",
            "title": "Signal generated",
            "summary": "Paper signal for RELIANCE.",
            "payload_json": {"confidence": "84%"},
        },
    )
    container.event_bus.publish(
        {
            "event_id": "evt-99",
            "event_type": "NEWS_EVENT_DETECTED",
            "source": "news-feed",
            "symbol": "RELIANCE",
            "severity": "WARNING",
            "description": "Headline detected",
            "reason": "News spike",
            "action_taken": "Monitor",
        }
    )
    app = create_app(container)
    with TestClient(app) as client:
        notifications = client.get("/api/notifications", params={"symbol": "RELIANCE"}).json()
        latest = client.get("/api/notifications/latest").json()
        account = client.get("/api/telemetry/account").json()
        positions = client.get("/api/telemetry/positions").json()
        trades = client.get("/api/telemetry/trades").json()
        day_summary = client.get("/api/telemetry/day-summary").json()
        dashboard = client.get("/api/dashboard-state").json()
        html = client.get("/").text

    assert any(item["symbol"] == "RELIANCE" for item in notifications)
    assert latest
    assert account["capital_available"] == 482700.0
    assert positions[0]["symbol"] == "RELIANCE"
    assert any(item["symbol"] == "TCS" for item in trades)
    assert day_summary["total_day_pnl"] == 8500.0
    assert dashboard["notifications"]
    assert dashboard["events"]
    assert "Notifications" in html
    assert "Send Status Now" in html
