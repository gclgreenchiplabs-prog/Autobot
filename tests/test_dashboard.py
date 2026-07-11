import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from dashboard_server import app


def test_dashboard_shows_paper_mode():
    with TestClient(app) as client:
        response = client.get('/')
        assert response.status_code == 200
        assert 'PAPER MODE' in response.text
