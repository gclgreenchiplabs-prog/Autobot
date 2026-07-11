from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.http import event_bus, state_store

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "lifecycle": state_store.get("lifecycle") or {"status": "initialized", "mode": "paper", "kill_switch": False},
                "events": event_bus.list_events(),
            }
            await websocket.send_json(payload)
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
