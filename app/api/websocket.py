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
                "type": "market_data_status",
                "lifecycle": container.state_store.get("lifecycle")
                or {"status": "initialized", "mode": container.settings.trading_mode, "kill_switch": False},
                "events": container.event_bus.list_events(),
                "market_data_status": container.state_store.get("market_data_status") or {},
                "quote_update": (container.state_store.get("market_data_quotes") or [])[:10],
                "candle_update": (container.state_store.get("market_data_candles") or [])[:10],
                "subscription_update": container.state_store.get("market_data_subscriptions") or [],
                "heartbeat_update": (container.state_store.get("market_data_status") or {}).get("heartbeat", {}),
                "market_data_event": (container.state_store.get("market_data_events_live") or [])[:10],
            }
            await websocket.send_json(payload)
            await websocket.receive_text()
    except WebSocketDisconnect:
        return
