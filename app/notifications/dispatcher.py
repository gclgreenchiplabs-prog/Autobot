from __future__ import annotations

from typing import Any, Dict, Optional

from app.notifications.repository import NotificationRepository
from app.notifications.telegram import TelegramAdapter


class NotificationDispatcher:
    def __init__(
        self,
        repository: NotificationRepository,
        telegram_adapter: TelegramAdapter,
    ) -> None:
        self.repository = repository
        self.telegram_adapter = telegram_adapter

    def dispatch(self, notification: Dict[str, Any], message: str) -> Dict[str, Any]:
        notification_id = notification["notification_id"]
        channels = list(notification.get("delivery_channels") or ["telegram"])
        if "telegram" not in channels:
            channels.append("telegram")

        result = self.telegram_adapter.send(message)
        self.repository.save_delivery_attempt(
            notification_id=notification_id,
            channel="telegram",
            status=result["status"],
            attempt_number=result["attempts"],
            error=result.get("error"),
            response={"parts": result.get("parts", 0)},
        )
        self.repository.update_delivery_status(
            notification_id=notification_id,
            delivery_status=result["status"],
            delivery_attempts=result["attempts"],
            delivery_error=result.get("error"),
            delivery_channels=channels,
        )
        return self.repository.get_notification(notification_id) or notification
