from __future__ import annotations

from typing import Any, Dict

from app.lifecycle import AppLifecycle
from app.notifications.models import NotificationSeverity, NotificationType
from app.notifications.service import NotificationService
from app.state_store import StateStore


class ControlService:
    def __init__(
        self,
        state_store: StateStore | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.state_store = state_store or StateStore()
        self.lifecycle = AppLifecycle(state_store=self.state_store)
        self.notification_service = notification_service

    def apply(self, action: str) -> Dict[str, Any]:
        if action == "start":
            payload = self.lifecycle.start()
            self._notify(NotificationType.BOT_STARTED.value, payload)
            return payload
        if action == "stop":
            payload = self.lifecycle.stop()
            self._notify(NotificationType.BOT_STOPPED.value, payload)
            return payload
        if action == "pause":
            payload = self.lifecycle.pause()
            self._notify(NotificationType.BOT_PAUSED.value, payload, severity=NotificationSeverity.WARNING.value)
            return payload
        if action == "resume":
            payload = self.lifecycle.resume()
            self._notify(NotificationType.BOT_RESUMED.value, payload)
            return payload
        if action == "scan":
            self.state_store.set("scan_requested", True)
            return {"status": "queued", "action": action}
        if action == "kill-switch":
            payload = self.lifecycle.trigger_kill_switch()
            self._notify(NotificationType.KILL_SWITCH_TRIGGERED.value, payload, severity=NotificationSeverity.CRITICAL.value)
            return payload
        raise ValueError(f"unsupported action: {action}")

    def _notify(self, notification_type: str, payload: Dict[str, Any], severity: str = NotificationSeverity.INFO.value) -> None:
        if self.notification_service is None:
            return
        self.notification_service.create_notification(
            notification_type,
            {
                "title": notification_type.replace("_", " "),
                "summary": f"Lifecycle changed to {payload.get('status')}.",
                "reason": f"Control action changed lifecycle to {payload.get('status')}.",
                "payload_json": payload,
            },
            severity=severity,
            dispatch=self.notification_service.settings.enable_notifications,
        )
