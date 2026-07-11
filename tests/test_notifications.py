import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.container import AppContainer
from app.notifications.models import NotificationRecord, NotificationType
from app.notifications.telegram import TelegramAdapter
from app.settings import Settings


def build_container(tmp_path, **settings_overrides):
    settings = Settings(
        database_path=str(tmp_path / "notifications.db"),
        forced_test_mode=True,
        **settings_overrides,
    )
    container = AppContainer(settings=settings)
    container.repository.initialize_schema()
    container.migrations.apply()
    container.wire_runtime()
    return container


def test_notification_model_validation(tmp_path):
    container = build_container(tmp_path)
    record = NotificationRecord.create(
        NotificationType.SIGNAL_GENERATED.value,
        payload={
            "symbol": "RELIANCE",
            "strategy": "Intraday Momentum",
            "delivery_channels": ["telegram"],
        },
    )
    assert record.notification_id
    assert record.notification_type == NotificationType.SIGNAL_GENERATED.value
    assert record.timestamp_utc
    assert record.timestamp_ist
    assert record.payload_json["symbol"] == "RELIANCE"


def test_event_bus_subscription_creates_notification(tmp_path):
    container = build_container(tmp_path)
    container.notification_service.start()
    container.event_bus.publish(
        {
            "event_id": "evt-1",
            "event_type": "BROKER_DISCONNECTED",
            "source": "broker-monitor",
            "symbol": "NIFTY",
            "severity": "ERROR",
            "detected_at": "2026-07-11T09:15:00+00:00",
            "title": "Broker disconnect",
            "description": "Primary broker lost connectivity.",
            "reason": "Socket timeout",
            "action_taken": "Fallback monitoring enabled",
        }
    )
    notifications = container.notification_service.list_notifications(symbol="NIFTY")
    assert any(item["notification_type"] == "BROKER_DISCONNECTED" for item in notifications)


def test_telegram_disabled_mode_and_secrets_not_exposed(tmp_path):
    container = build_container(
        tmp_path,
        enable_telegram=False,
        telegram_bot_token="123456:SUPERSECRET-TOKEN",
        telegram_chat_id="998877",
    )
    container.notification_service.start()
    notification = container.notification_service.create_notification(
        NotificationType.BOT_HEARTBEAT.value,
        {"title": "Heartbeat", "summary": "Bot heartbeat."},
    )
    serialized = json.dumps(notification)
    assert notification["delivery_status"] == "DISABLED"
    assert "SUPERSECRET-TOKEN" not in serialized
    assert container.telegram_adapter.masked_token() != "123456:SUPERSECRET-TOKEN"


def test_telegram_retry_behavior_with_mocked_transport():
    calls = {"count": 0}

    def flaky_transport(message, payload):
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary failure")
        return {"status_code": 200, "body": "ok"}

    adapter = TelegramAdapter(
        Settings(enable_telegram=True, telegram_bot_token="token1234", telegram_chat_id="chat1234"),
        transport=flaky_transport,
        sleep=lambda _: None,
    )
    result = adapter.send("hello world")
    assert result["status"] == "DELIVERED"
    assert result["attempts"] == 3


def test_long_message_splitting():
    sent = []

    def collect_transport(message, payload):
        sent.append(message)
        return {"status_code": 200, "body": "ok"}

    adapter = TelegramAdapter(
        Settings(enable_telegram=True, telegram_bot_token="token1234", telegram_chat_id="chat1234"),
        transport=collect_transport,
        sleep=lambda _: None,
        max_message_length=32,
    )
    result = adapter.send("A" * 80)
    assert result["status"] == "DELIVERED"
    assert len(sent) == 3
