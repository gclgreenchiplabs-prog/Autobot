import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.application import create_app
from app.container import AppContainer
from app.notifications.models import NotificationType
from app.settings import Settings


def build_container(tmp_path):
    container = AppContainer(
        settings=Settings(
            database_path=str(tmp_path / "status.db"),
            forced_test_mode=True,
            enable_notifications=True,
            status_send_unchanged=False,
        )
    )
    container.repository.initialize_schema()
    container.migrations.apply()
    container.wire_runtime()
    return container


def test_no_status_while_stopped(tmp_path):
    container = build_container(tmp_path)
    container.notification_service.start()
    result = container.notification_service.generate_status_report(force=False)
    assert result is None


def test_five_minute_scheduler_start_and_stop(tmp_path):
    async def exercise():
        container = build_container(tmp_path)
        container.notification_service.start()
        container.control_service.apply("start")
        container.status_scheduler.start()
        generated = await container.status_scheduler.run_once()
        container.status_scheduler.stop()
        return container, generated

    container, generated = asyncio.run(exercise())
    assert generated is not None
    assert generated["notification_type"] == NotificationType.FIVE_MINUTE_STATUS.value
    assert container.task_manager.get_task("status-notifications").state == "CANCELLED"


def test_status_now_endpoint(tmp_path):
    container = build_container(tmp_path)
    app = create_app(container)
    with TestClient(app) as client:
        client.post("/api/control/start")
        response = client.post("/api/control/send-status-now")
        assert response.status_code == 200
        assert response.json()["notification_type"] == NotificationType.FIVE_MINUTE_STATUS.value
