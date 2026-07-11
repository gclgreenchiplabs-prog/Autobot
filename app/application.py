from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.controls import ControlService
from app.api.http import router as http_router
from app.api.middleware import CorrelationMiddleware, add_exception_middleware
from app.api.websocket import router as websocket_router
from app.container import AppContainer
from app.dashboard.service import DashboardService
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
    app.state.control_service = ControlService(state_store=runtime_container.state_store)
    app.state.dashboard_service = DashboardService(state_store=runtime_container.state_store)

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
            "lifecycle": dashboard_data["lifecycle"],
            "orders": dashboard_data["orders"],
            "positions": dashboard_data["positions"],
            "broker": container.settings.primary_broker,
            "health": container.health_monitor.snapshot(),
            "session": container.scheduler.get_state(),
            "tasks": container.task_manager.get_status(),
        }

    return app


app = create_app()

__all__ = ["CANONICAL_APP_IMPORT_PATH", "app", "create_app"]
