import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import create_app
from app.container import AppContainer
from app.settings import Settings


def build_client(tmp_path: Path, settings: Settings) -> TestClient:
    container = AppContainer(settings=settings)
    container.instrument_service.import_instruments({"source": "FIXTURE"})
    return TestClient(create_app(container))


def test_configured_brokers_report_configured_not_connected_in_paper_fixture_mode(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "paper_fixture.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="paper",
        market_data_mode="FIXTURE",
        primary_broker="fyers",
        standby_broker="dhan",
        execution_broker="fyers",
        primary_market_data_broker="fyers",
        standby_market_data_broker="dhan",
        fyers_configured=True,
        dhan_configured=True,
    )

    with build_client(tmp_path, settings) as client:
        health = client.get("/health").json()
        state = client.get("/api/state").json()
        readiness = client.get("/api/readiness").json()
        dashboard = client.get("/api/dashboard-state").json()

    for payload in (health, state, readiness):
        assert payload["execution_mode"] == "paper"
        assert payload["configured_primary_broker"] == "fyers"
        assert payload["active_execution_broker"] == "paper"
        assert payload["standby_broker"] == "dhan"
        assert payload["brokers"]["fyers"]["status"] == "CONFIGURED"
        assert payload["brokers"]["dhan"]["status"] == "CONFIGURED"
        assert payload["brokers"]["fyers"]["configured"] is True
        assert payload["brokers"]["dhan"]["configured"] is True
        assert payload["brokers"]["fyers"]["connected"] is False
        assert payload["brokers"]["dhan"]["connected"] is False
        assert payload["brokers"]["fyers"]["execution_ready"] is False
        assert payload["brokers"]["dhan"]["execution_ready"] is False

    assert state["broker"]["connected"] is False
    assert readiness["active_market_data_source"] == "fixture"
    assert dashboard["broker_readiness"]["fyers"]["status"] == "CONFIGURED"
    assert dashboard["broker_readiness"]["dhan"]["status"] == "CONFIGURED"


def test_live_market_data_mode_rejects_missing_credentials_and_keeps_execution_independent(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "live_data_blocked.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="paper",
        market_data_mode="LIVE",
        live_market_data_enable=True,
        primary_market_data_broker="fyers",
        standby_market_data_broker="dhan",
        fyers_configured=True,
        fyers_market_data_enable=True,
        dhan_configured=True,
    )

    with build_client(tmp_path, settings) as client:
        readiness = client.get("/api/readiness").json()
        status = client.get("/api/market-data/status").json()
        connections = client.get("/api/market-data/connections").json()

    assert readiness["execution_mode"] == "paper"
    assert readiness["active_execution_broker"] == "paper"
    assert readiness["market_data_mode"] == "live"
    assert readiness["active_market_data_source"] == "fyers"
    assert readiness["brokers"]["fyers"]["capabilities"]["market_data"]["status"] == "CREDENTIALS_MISSING"
    assert readiness["brokers"]["fyers"]["execution_ready"] is False
    assert status["brokers"]["fyers"]["market_data_ready"] is False
    assert isinstance(connections["connections"], list)
    assert connections["brokers"]["fyers"]["status"] == "CONFIGURED"


def test_live_execution_requires_explicit_confirmation_for_fyers(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "live_exec_fyers_blocked.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="live",
        live_order_enable=True,
        explicit_live_confirmation=False,
        market_data_mode="LIVE",
        live_market_data_enable=True,
        primary_broker="fyers",
        execution_broker="fyers",
        primary_market_data_broker="fyers",
        fyers_configured=True,
        fyers_execution_enable=True,
        fyers_market_data_enable=True,
        fyers_client_id="client-id",
        fyers_secret_key="secret-key",
        fyers_access_token="access-token",
    )

    container = AppContainer(settings=settings)
    snapshot = container.broker_readiness_service.snapshots()["fyers"]
    execution = snapshot["capabilities"]["execution"]
    market_data = snapshot["capabilities"]["market_data"]

    assert snapshot["configured"] is True
    assert execution["status"] == "DISABLED"
    assert execution["reason"] == "EXPLICIT_LIVE_CONFIRMATION is false."
    assert market_data["status"] in {"SDK_NOT_INSTALLED", "AUTHENTICATION_REQUIRED", "FAILED", "DISCONNECTED", "DEGRADED", "CONNECTED", "READY", "CREDENTIALS_MISSING"}
    assert snapshot["execution_ready"] is False


def test_dhan_live_execution_requires_order_api_and_static_ip(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "live_exec_dhan_blocked.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="live",
        live_order_enable=True,
        explicit_live_confirmation=True,
        enable_execution_failover=True,
        execution_failover_approved=True,
        primary_broker="fyers",
        standby_broker="dhan",
        execution_broker="dhan",
        dhan_configured=True,
        dhan_execution_enable=True,
        dhan_client_id="dhan-client",
        dhan_access_token="dhan-token",
        dhan_order_api_enable=False,
        dhan_static_ip_ready=False,
    )

    container = AppContainer(settings=settings)
    snapshot = container.broker_readiness_service.snapshots()["dhan"]
    execution = snapshot["capabilities"]["execution"]

    assert snapshot["configured"] is True
    assert execution["status"] == "DISABLED"
    assert execution["reason"] == "DHAN_ORDER_API_ENABLE is false."
    assert snapshot["execution_ready"] is False
    assert snapshot["active"] is True


def test_dhan_live_execution_requires_static_ip_when_order_api_is_enabled(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "live_exec_dhan_static_ip_blocked.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="live",
        live_order_enable=True,
        explicit_live_confirmation=True,
        enable_execution_failover=True,
        execution_failover_approved=True,
        execution_broker="dhan",
        dhan_configured=True,
        dhan_execution_enable=True,
        dhan_client_id="dhan-client",
        dhan_access_token="dhan-token",
        dhan_order_api_enable=True,
        dhan_static_ip_ready=False,
    )

    container = AppContainer(settings=settings)
    snapshot = container.broker_readiness_service.snapshots()["dhan"]
    execution = snapshot["capabilities"]["execution"]

    assert execution["status"] == "DISABLED"
    assert execution["reason"] == "DHAN_STATIC_IP_READY is false."
    assert snapshot["execution_ready"] is False


def test_dhan_live_execution_requires_failover_approval_for_standby_use(tmp_path: Path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "live_exec_dhan_failover_blocked.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="live",
        live_order_enable=True,
        explicit_live_confirmation=True,
        enable_execution_failover=True,
        execution_failover_approved=False,
        primary_broker="fyers",
        standby_broker="dhan",
        execution_broker="dhan",
        dhan_configured=True,
        dhan_execution_enable=True,
        dhan_client_id="dhan-client",
        dhan_access_token="dhan-token",
        dhan_order_api_enable=True,
        dhan_static_ip_ready=True,
    )

    container = AppContainer(settings=settings)
    snapshot = container.broker_readiness_service.snapshots()["dhan"]
    execution = snapshot["capabilities"]["execution"]

    assert execution["status"] == "DISABLED"
    assert execution["reason"] == "EXECUTION_FAILOVER_APPROVED is false."


def test_broker_credentials_never_appear_in_api_dashboard_or_notifications(tmp_path: Path) -> None:
    secret_values = ["fyers-secret-token", "dhan-secret-token", "super-secret-key"]
    settings = Settings(
        database_path=str(tmp_path / "secret_hygiene.db"),
        forced_test_mode=True,
        enable_notifications=False,
        trading_mode="paper",
        market_data_mode="FIXTURE",
        fyers_configured=True,
        dhan_configured=True,
        fyers_client_id="fyers-client",
        fyers_secret_key=secret_values[2],
        fyers_access_token=secret_values[0],
        dhan_client_id="dhan-client",
        dhan_access_token=secret_values[1],
    )

    with build_client(tmp_path, settings) as client:
        payloads = [
            client.get("/health").json(),
            client.get("/api/state").json(),
            client.get("/api/readiness").json(),
            client.get("/api/dashboard-state").json(),
            client.get("/api/market-data/status").json(),
            client.get("/api/market-data/connections").json(),
            client.get("/api/notifications/latest").json(),
        ]

    serialized = json.dumps(payloads, sort_keys=True)
    for secret in secret_values:
        assert secret not in serialized
