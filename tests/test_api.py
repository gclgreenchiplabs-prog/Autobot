import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from dashboard_server import app as dashboard_app
from main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['mode'] == 'paper'


def test_dashboard_app_reuses_main_app_instance():
    assert dashboard_app is app


def test_control_endpoints():
    for action in ['start', 'stop', 'pause', 'resume', 'scan', 'kill-switch']:
        response = client.post(f'/api/control/{action}')
        assert response.status_code == 200
