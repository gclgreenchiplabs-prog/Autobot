from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.database.repository import Repository


class NotificationRepository:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def create(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        self.repository.save_notification(notification)
        return notification

    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        return self.repository.get_notification(notification_id)

    def list_notifications(
        self,
        *,
        notification_type: Optional[str] = None,
        severity: Optional[str] = None,
        symbol: Optional[str] = None,
        trade_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        return self.repository.list_notifications(
            notification_type=notification_type,
            severity=severity,
            symbol=symbol,
            trade_id=trade_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repository.list_notifications(limit=limit)

    def list_by_trade(self, trade_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.repository.list_notifications(trade_id=trade_id, limit=limit)

    def list_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.repository.list_notifications(symbol=symbol, limit=limit)

    def save_delivery_attempt(
        self,
        *,
        notification_id: str,
        channel: str,
        status: str,
        attempt_number: int,
        error: Optional[str] = None,
        response: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.repository.save_notification_delivery_attempt(
            notification_id=notification_id,
            channel=channel,
            status=status,
            attempt_number=attempt_number,
            error=error,
            response=response or {},
        )

    def update_delivery_status(
        self,
        *,
        notification_id: str,
        delivery_status: str,
        delivery_attempts: int,
        delivery_error: Optional[str],
        delivery_channels: List[str],
    ) -> None:
        self.repository.update_notification_delivery(
            notification_id=notification_id,
            delivery_status=delivery_status,
            delivery_attempts=delivery_attempts,
            delivery_error=delivery_error,
            delivery_channels=delivery_channels,
        )
