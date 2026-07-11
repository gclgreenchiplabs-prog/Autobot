import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.notifications.models import NotificationType
from app.settings import Settings


def build_container(db_path: Path) -> AppContainer:
    container = AppContainer(
        settings=Settings(
            database_path=str(db_path),
            forced_test_mode=True,
        )
    )
    container.repository.initialize_schema()
    container.migrations.apply()
    container.wire_runtime()
    return container


def test_notification_persistence_survives_restart(tmp_path):
    db_path = tmp_path / "persist.db"
    container = build_container(db_path)
    container.notification_service.start()
    created = container.notification_service.create_notification(
        NotificationType.CAPITAL_UPDATED.value,
        {
            "title": "Capital updated",
            "summary": "Capital moved after paper fill.",
            "capital_available": 491150.0,
        },
    )
    container.database.close()

    restarted = build_container(db_path)
    reloaded = restarted.notification_repository.get_notification(created["notification_id"])
    assert reloaded is not None
    assert reloaded["title"] == "Capital updated"


def test_delivery_attempt_persistence(tmp_path):
    db_path = tmp_path / "delivery.db"
    container = build_container(db_path)
    container.notification_service.start()
    created = container.notification_service.create_notification(
        NotificationType.BOT_HEARTBEAT.value,
        {"title": "Heartbeat", "summary": "Paper heartbeat."},
    )
    attempts = container.repository.list_delivery_attempts(created["notification_id"])
    assert attempts
    assert attempts[0]["status"] == "DISABLED"
