from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.http import state_store
from app.settings import Settings

app = FastAPI(title="MARKET MOVE AI Dashboard")
settings = Settings()
BASE_DIR = Path(__file__).resolve().parent / "app" / "dashboard"
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    return html.replace("{{MODE}}", settings.trading_mode.upper())


@app.get("/api/dashboard-state")
def dashboard_state() -> dict:
    return {
        "mode": settings.trading_mode,
        "lifecycle": state_store.get("lifecycle") or {"status": "initialized", "mode": settings.trading_mode, "kill_switch": False},
        "broker": settings.primary_broker,
    }
