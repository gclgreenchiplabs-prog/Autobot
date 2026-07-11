from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.event_bus import EventBus
from app.health import HealthMonitor
from app.notifications.dispatcher import NotificationDispatcher
from app.notifications.formatter import NotificationFormatter
from app.notifications.models import NotificationRecord, NotificationSeverity, NotificationType
from app.notifications.repository import NotificationRepository
from app.scheduler.session_scheduler import SessionScheduler
from app.settings import Settings
from app.state_store import StateStore
from app.telemetry import TelemetryService


class NotificationService:
    ACTIVE_SESSION_STATES = {"PREMARKET", "MARKET_OPEN", "POST_MARKET", "FORCED_TEST"}

    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        notification_repository: NotificationRepository,
        telemetry_service: TelemetryService,
        formatter: NotificationFormatter,
        dispatcher: NotificationDispatcher,
        event_bus: EventBus,
        scheduler: SessionScheduler,
        health_monitor: HealthMonitor,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.notification_repository = notification_repository
        self.telemetry_service = telemetry_service
        self.formatter = formatter
        self.dispatcher = dispatcher
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.health_monitor = health_monitor
        self._event_subscription_registered = False
        self._last_status_signature: Optional[str] = None

    def start(self) -> None:
        self.subscribe_event_bus()
        self.state_store.set("notification_service", {"enabled": self.settings.enable_notifications})
        self.create_notification(
            NotificationType.BOT_STARTED.value,
            {
                "title": "Bot started",
                "summary": "Notification service initialized.",
                "event_source": "startup",
                "reason": "Application startup completed.",
            },
            dispatch=self.settings.enable_notifications,
        )

    def stop(self) -> None:
        self.create_notification(
            NotificationType.BOT_STOPPED.value,
            {
                "title": "Bot stopped",
                "summary": "Notification service shutting down.",
                "event_source": "shutdown",
                "reason": "Application shutdown requested.",
            },
            dispatch=self.settings.enable_notifications,
        )

    def subscribe_event_bus(self) -> None:
        if self._event_subscription_registered:
            return
        self.event_bus.subscribe(self._handle_event)
        self._event_subscription_registered = True

    def _base_context(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="notification-context")
        return {
            "day_realized_pnl": account.realized_pnl,
            "day_unrealized_pnl": account.unrealized_pnl,
            "day_total_pnl": account.total_day_pnl,
            "capital_used_day": account.capital_used_day,
            "capital_reserved": account.capital_reserved,
            "capital_available": account.capital_available,
            "account_equity": account.account_equity,
            "execution_mode": account.execution_mode,
            "configured_primary_broker": account.configured_primary_broker,
            "active_execution_broker": account.active_execution_broker,
            "standby_broker": account.standby_broker,
        }

    def create_notification(
        self,
        notification_type: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        severity: str = NotificationSeverity.INFO.value,
        dispatch: bool = True,
    ) -> Dict[str, Any]:
        merged_payload = {**self._base_context(), **dict(payload or {})}
        merged_payload.setdefault("delivery_channels", ["telegram"])
        notification = NotificationRecord.create(
            notification_type=notification_type,
            payload=merged_payload,
            severity=severity,
            timezone_name=self.settings.timezone,
        )

        formatted = self.formatter.format(notification)
        if not notification.title:
            notification.title = formatted["title"]
        if not notification.summary:
            notification.summary = formatted["summary"]

        persisted = notification.to_dict()
        self.notification_repository.create(persisted)
        self.telemetry_service.persist_snapshots(reason=f"notification:{notification_type}")

        if dispatch:
            return self.dispatcher.dispatch(persisted, formatted["body"])
        self.notification_repository.update_delivery_status(
            notification_id=notification.notification_id,
            delivery_status="PERSISTED",
            delivery_attempts=0,
            delivery_error=None,
            delivery_channels=notification.delivery_channels or ["telegram"],
        )
        return self.notification_repository.get_notification(notification.notification_id) or persisted

    def list_notifications(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.notification_repository.list_notifications(**filters)

    def latest_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.notification_repository.latest(limit=limit)

    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        return self.notification_repository.get_notification(notification_id)

    def notifications_by_trade(self, trade_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.notification_repository.list_by_trade(trade_id=trade_id, limit=limit)

    def notifications_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.notification_repository.list_by_symbol(symbol=symbol, limit=limit)

    def _status_signature(self, payload: Dict[str, Any]) -> str:
        signature_payload = {
            "system": {
                "bot_state": payload["system"]["bot_state"],
                "session_state": payload["system"]["session_state"],
                "execution_mode": payload["system"]["execution_mode"],
                "data_state": payload["system"]["data_state"],
                "health_status": payload["system"]["health_status"],
            },
            "account": payload["account"],
            "open_positions": payload["open_positions"],
            "recently_closed_positions": payload["recently_closed_positions"],
            "recent_events": payload["recent_events"],
        }
        return json.dumps(signature_payload, sort_keys=True, default=str)

    def should_generate_status(self) -> bool:
        if not self.settings.enable_notifications:
            return False
        lifecycle = self.state_store.get("lifecycle") or {}
        if lifecycle.get("status") != "running":
            return False
        session_state = self.scheduler.get_state()["session_state"]
        return session_state in self.ACTIVE_SESSION_STATES

    def build_status_payload(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="status-report").to_dict()
        positions = [snapshot.to_dict() for snapshot in self.telemetry_service.build_position_snapshots()]
        recent_closed = [
            snapshot.to_dict()
            for snapshot in self.telemetry_service.recent_closed_trades(self.settings.status_recent_closed_window_minutes)
        ] if self.settings.status_include_recent_closed else []
        health = self.health_monitor.snapshot()
        session = self.scheduler.get_state()
        lifecycle = self.state_store.get("lifecycle") or {"status": "initialized", "mode": self.settings.trading_mode, "kill_switch": False}
        recent_events = self.event_bus.list_events()[-10:]
        return {
            "system": {
                "bot_state": lifecycle.get("status"),
                "session_state": session.get("session_state"),
                "current_ist_time": session.get("ist_time"),
                "execution_mode": account["execution_mode"],
                "data_state": self.state_store.get("data_feed_state", "UNKNOWN"),
                "primary_broker": account["configured_primary_broker"],
                "active_broker": account["active_execution_broker"],
                "standby_broker": account["standby_broker"],
                "health_status": health.get("status"),
            },
            "account": account,
            "open_positions": positions,
            "recently_closed_positions": recent_closed,
            "recent_events": recent_events,
        }

    def generate_status_report(self, *, force: bool = False, source: str = "scheduler") -> Optional[Dict[str, Any]]:
        if not force and not self.should_generate_status():
            return None
        payload = self.build_status_payload()
        signature = self._status_signature(payload)
        if not force and not self.settings.status_send_unchanged and signature == self._last_status_signature:
            return None
        self._last_status_signature = signature
        return self.create_notification(
            NotificationType.FIVE_MINUTE_STATUS.value,
            {
                "event_source": source,
                "title": "Five minute status report",
                "summary": "Periodic system status report generated.",
                "payload_json": payload,
            },
            severity=NotificationSeverity.INFO.value,
            dispatch=self.settings.enable_notifications,
        )

    def _handle_event(self, event: Dict[str, Any]) -> None:
        event_type = self._coerce_event_notification_type(event)
        self.create_notification(
            event_type,
            {
                "severity": str(event.get("severity") or NotificationSeverity.INFO.value).upper(),
                "symbol": event.get("symbol"),
                "exchange": event.get("exchange"),
                "title": event.get("title") or str(event.get("event_type") or event_type).replace("_", " "),
                "summary": event.get("description") or event.get("reason") or "Event detected.",
                "reason": event.get("reason"),
                "event_source": event.get("source"),
                "payload_json": dict(event),
            },
            severity=str(event.get("severity") or NotificationSeverity.INFO.value).upper(),
            dispatch=self.settings.enable_notifications,
        )

    def _coerce_event_notification_type(self, event: Dict[str, Any]) -> str:
        raw_type = str(event.get("event_type") or "").strip().upper()
        if raw_type in {member.value for member in NotificationType}:
            return raw_type
        if raw_type.startswith(("INSTRUMENT_", "DATA_QUALITY_", "QUOTE_", "LIQUIDITY_", "SPREAD_", "UNIVERSE_")):
            return raw_type
        if "CORPORATE" in raw_type:
            return NotificationType.CORPORATE_EVENT_DETECTED.value
        if "NEWS" in raw_type:
            return NotificationType.NEWS_EVENT_DETECTED.value
        if "VOLATILITY" in raw_type:
            return NotificationType.VOLATILITY_EVENT_DETECTED.value
        if "LIQUIDITY" in raw_type:
            return NotificationType.LIQUIDITY_EVENT_DETECTED.value
        return NotificationType.MARKET_EVENT_DETECTED.value
