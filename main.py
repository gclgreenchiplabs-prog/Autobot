from fastapi import FastAPI

from app.api.http import router as http_router
from app.api.websocket import router as websocket_router
from app.logging_setup import configure_logging

app = FastAPI(title="MARKET MOVE AI")
configure_logging()
app.include_router(http_router)
app.include_router(websocket_router)
