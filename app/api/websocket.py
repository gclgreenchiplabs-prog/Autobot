from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            container = websocket.app.state.container
            payload = {
                "lifecycle": container.state_store.get("lifecycle")
                or {"status": "initialized", "mode": container.settings.trading_mode, "kill_switch": False},
                "events": container.event_bus.list_events(),
            }
            await websocket.send_json(payload)
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
