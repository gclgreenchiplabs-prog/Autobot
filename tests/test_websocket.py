import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from main import app


def test_websocket_streams_state():
    with TestClient(app) as client:
        with client.websocket_connect('/ws') as websocket:
            message = websocket.receive_json()
            assert 'lifecycle' in message
            assert 'events' in message
            assert 'market_data_status' in message
            assert 'quote_update' in message
