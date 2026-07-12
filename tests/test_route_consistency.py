import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.application import CANONICAL_APP_IMPORT_PATH, app as canonical_app
from dashboard_server import app as dashboard_app
from main import app as main_app

REQUIRED_ROUTES = [
    "/health",
    "/api/state",
    "/api/readiness",
    "/api/tasks",
    "/api/session",
    "/api/database/status",
    "/api/orders",
    "/api/positions",
    "/api/events",
    "/api/companies",
    "/api/instruments",
    "/api/universe/status",
    "/api/universe/conflicts",
    "/api/universe/fno",
    "/api/universe/nse",
    "/api/universe/bse",
    "/api/market-data/quality",
    "/api/market-data/stale",
    "/api/market-data/liquidity",
    "/api/market-data/status",
    "/api/market-data/connections",
    "/api/market-data/subscriptions",
    "/api/market-data/quotes",
    "/api/market-data/quotes/{instrument_id}",
    "/api/market-data/candles",
    "/api/market-data/candles/{instrument_id}",
    "/api/market-data/rejections",
    "/api/market-data/events",
    "/api/market-data/heartbeat",
    "/api/audit/timeline",
    "/api/scanner/candidates",
    "/api/scanner/summary",
    "/api/scanner/intraday",
    "/api/scanner/btst",
    "/api/scanner/swing",
    "/api/scanner/portfolio",
    "/api/scanner/options",
    "/api/scanner/watchlist",
    "/api/scanner/avoid",
    "/api/scanner/regime",
    "/api/control/start",
    "/api/control/stop",
    "/api/control/pause",
    "/api/control/resume",
    "/api/control/scan",
    "/api/control/kill-switch",
    "/api/control/import-instruments",
    "/api/control/market-data/connect",
    "/api/control/market-data/disconnect",
    "/api/control/market-data/subscribe",
    "/api/control/market-data/unsubscribe",
    "/api/control/market-data/reconnect",
    "/api/control/market-data/start-fixture",
    "/api/control/market-data/stop-fixture",
    "/ws",
    "/static",
    "/",
    "/api/dashboard-state",
]


def test_canonical_app_is_shared_and_routes_are_unique():
    assert canonical_app is main_app
    assert canonical_app is dashboard_app
    assert canonical_app.state.canonical_import_path == CANONICAL_APP_IMPORT_PATH
    assert canonical_app.state.container is canonical_app.state.startup_manager.container
    assert canonical_app.state.startup_manager.app is canonical_app
    assert canonical_app.state.control_service.state_store is canonical_app.state.container.state_store
    assert canonical_app.state.telemetry_service is canonical_app.state.container.telemetry_service
    assert canonical_app.state.notification_service is canonical_app.state.container.notification_service
    assert canonical_app.state.market_data_service is canonical_app.state.container.market_data_service
    assert canonical_app.state.dashboard_service.telemetry_service is canonical_app.state.container.telemetry_service

    route_counts = Counter(route.path for route in canonical_app.routes if hasattr(route, "path"))

    for path in REQUIRED_ROUTES:
        assert route_counts[path] == 1, f"{path} count was {route_counts[path]}"
