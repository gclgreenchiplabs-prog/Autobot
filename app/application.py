from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.http import router as http_router
from app.api.middleware import CorrelationMiddleware, add_exception_middleware
from app.api.websocket import router as websocket_router
from app.container import AppContainer
from app.logging_setup import configure_logging
from app.startup import ApplicationStartupManager

CANONICAL_APP_IMPORT_PATH = "app.application:app"


def create_app(container: AppContainer | None = None) -> FastAPI:
    runtime_container = container or AppContainer()
    startup_manager = ApplicationStartupManager(app=None, container=runtime_container)
    app = FastAPI(title="MARKET MOVE AI", lifespan=startup_manager.lifespan)
    startup_manager.app = app

    configure_logging(log_dir="logs")
    app.state.canonical_import_path = CANONICAL_APP_IMPORT_PATH
    app.state.container = runtime_container
    app.state.startup_manager = startup_manager
    app.state.control_service = runtime_container.control_service
    app.state.dashboard_service = runtime_container.dashboard_service
    app.state.notification_service = runtime_container.notification_service
    app.state.telemetry_service = runtime_container.telemetry_service
    app.state.instrument_service = runtime_container.instrument_service
    app.state.market_data_repository = runtime_container.market_data_repository

    add_exception_middleware(app)
    app.add_middleware(CorrelationMiddleware)
    app.include_router(http_router)
    app.include_router(websocket_router)

    base_dir = Path(__file__).resolve().parent / "dashboard"
    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        html = (base_dir / "templates" / "index.html").read_text(encoding="utf-8")
        return html.replace("{{MODE}}", runtime_container.settings.trading_mode.upper())

    @app.get("/api/dashboard-state")
    def dashboard_state(request: Request) -> dict:
        container = request.app.state.container
        dashboard_service = request.app.state.dashboard_service
        dashboard_data = dashboard_service.get_state()
        return {
            "mode": container.settings.trading_mode,
            "lifecycle": container.state_store.get("lifecycle") or {"status": "initialized", "mode": container.settings.trading_mode, "kill_switch": False},
            "orders": container.state_store.get("orders", []),
            "positions": container.state_store.get("positions", []),
            "broker": container.settings.primary_broker,
            "database_path": container.settings.database_path,
            "account_summary": dashboard_data["account_summary"],
            "open_positions": dashboard_data["open_positions"],
            "recently_exited": dashboard_data["recently_exited"],
            "notifications": dashboard_data["notifications"],
            "events": dashboard_data["detected_events"],
            "universe_summary": dashboard_data["universe_summary"],
            "broker_mapping_summary": dashboard_data["broker_mapping_summary"],
            "data_quality_summary": dashboard_data["data_quality_summary"],
            "liquidity_summary": dashboard_data["liquidity_summary"],
            "stale_data_summary": dashboard_data["stale_data_summary"],
            "instrument_table": dashboard_data["instrument_table"],
            "conflicts": dashboard_data["conflicts"],
            "health": dashboard_data["health"],
            "session": dashboard_data["session"],
            "tasks": dashboard_data["tasks"],
        }

    return app


app = create_app()

__all__ = ["CANONICAL_APP_IMPORT_PATH", "app", "create_app"]
