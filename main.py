from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.http import router as http_router
from app.api.http import state_store
from app.api.middleware import CorrelationMiddleware, add_exception_middleware
from app.api.websocket import router as websocket_router
from app.container import AppContainer
from app.logging_setup import configure_logging
from app.settings import Settings
from app.startup import ApplicationStartupManager


container = AppContainer()


def create_app() -> FastAPI:
    app = FastAPI(title="MARKET MOVE AI", lifespan=ApplicationStartupManager(app=None, container=container).lifespan)
    configure_logging(log_dir="logs")
    add_exception_middleware(app)
    app.add_middleware(CorrelationMiddleware)
    app.include_router(http_router)
    app.include_router(websocket_router)

    settings = Settings()
    base_dir = Path(__file__).resolve().parent / "app" / "dashboard"
    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        html = (base_dir / "templates" / "index.html").read_text(encoding="utf-8")
        return html.replace("{{MODE}}", settings.trading_mode.upper())

    @app.get("/api/dashboard-state")
    def dashboard_state() -> dict:
        return {
            "mode": settings.trading_mode,
            "lifecycle": state_store.get("lifecycle") or {"status": "initialized", "mode": settings.trading_mode, "kill_switch": False},
            "broker": settings.primary_broker,
            "health": container.health_monitor.snapshot(),
            "session": container.scheduler.get_state(),
            "tasks": container.task_manager.get_status(),
        }

    @app.get("/api/tasks")
    def tasks() -> list[dict]:
        return container.task_manager.get_status()

    @app.get("/api/session")
    def session() -> dict:
        return container.scheduler.get_state()

    @app.get("/api/database/status")
    def database_status() -> dict:
        return {"database_path": container.settings.database_path, "ready": True}

    return app


app = create_app()
