import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.models import OrderRequest
from app.settings import Settings


def build_container(tmp_path: Path, **overrides) -> AppContainer:
    settings = Settings(
        database_path=str(tmp_path / "execution.db"),
        forced_test_mode=True,
        enable_notifications=False,
        brokerage_flat_per_order=20.0,
        exchange_txn_pct=0.01,
        sebi_charges_pct=0.0001,
        gst_pct=18.0,
        stamp_duty_buy_pct=0.003,
        stt_sell_pct=0.025,
        **overrides,
    )
    container = AppContainer(settings=settings)
    container.state_store.set("lifecycle", {"status": "running", "mode": settings.trading_mode, "kill_switch": False})
    container.state_store.set("account", {"opening_capital": 500000.0, "capital_reserved": 0.0})
    return container


def test_paper_order_fill_creates_order_position_and_entry_charges(tmp_path: Path) -> None:
    container = build_container(tmp_path)

    result = container.execution_service.place_order(
        OrderRequest(symbol="RELIANCE", quantity=100, action="BUY", price=100.0)
    )

    assert result["status"] == "FILLED"
    assert result["capital_required"] == 10000.0
    assert result["charges"]["total"] > 0
    assert container.state_store.get("orders")
    assert container.state_store.get("positions")

    account = container.telemetry_service.build_account_snapshot(reason="test").to_dict()
    assert account["capital_used_day"] == 10000.0
    assert account["capital_available"] == 490000.0


def test_exit_position_computes_net_pnl_after_broker_charges(tmp_path: Path) -> None:
    container = build_container(tmp_path)
    placed = container.execution_service.place_order(
        OrderRequest(symbol="TCS", quantity=50, action="BUY", price=200.0)
    )
    trade_id = placed["trade_id"]

    exited = container.execution_service.exit_position(trade_id, exit_price=220.0, reason="target hit")

    assert exited["gross_pnl"] == 1000.0
    assert exited["net_pnl"] < exited["gross_pnl"]
    assert exited["capital_released"] > 0

    account = container.telemetry_service.build_account_snapshot(reason="test").to_dict()
    assert account["realized_pnl"] == exited["net_pnl"]
    assert account["capital_used_day"] == 0.0
    assert account["capital_available"] > 500000.0


def test_execution_api_exposes_status_and_control_endpoints(tmp_path: Path) -> None:
    container = build_container(tmp_path)
    with TestClient(create_app(container)) as client:
        status = client.get("/api/execution/status").json()
        placed = client.post(
            "/api/control/order",
            json={"symbol": "INFY", "quantity": 10, "action": "BUY", "price": 1500.0},
        ).json()
        exited = client.post(
            "/api/control/exit",
            json={"trade_id": placed["trade_id"], "exit_price": 1515.0, "reason": "manual"},
        ).json()

    assert status["execution_mode"] == "paper"
    assert placed["status"] == "FILLED"
    assert exited["status"] == "CLOSED"
    assert exited["net_pnl"] < exited["gross_pnl"]
