from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional

from app.settings import Settings


class TelegramDeliveryError(RuntimeError):
    pass


class TelegramAdapter:
    def __init__(
        self,
        settings: Settings,
        transport: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        sleep: Optional[Callable[[float], None]] = None,
        max_message_length: int = 3500,
    ) -> None:
        self.settings = settings
        self.transport = transport or self._default_transport
        self.sleep = sleep or time.sleep
        self.max_message_length = max_message_length

    @property
    def enabled(self) -> bool:
        return bool(self.settings.enable_telegram and self.settings.telegram_bot_token and self.settings.telegram_chat_id)

    def masked_token(self) -> str:
        token = self.settings.telegram_bot_token or ""
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}***{token[-4:]}"

    def split_message(self, message: str) -> List[str]:
        if len(message) <= self.max_message_length:
            return [message]
        chunks: List[str] = []
        remaining = message
        while remaining:
            if len(remaining) <= self.max_message_length:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n", 0, self.max_message_length)
            if split_at <= 0:
                split_at = self.max_message_length
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()
        return chunks

    def send(self, message: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "DISABLED", "attempts": 0, "error": None, "parts": 0}

        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "parse_mode": self.settings.telegram_parse_mode,
            "disable_web_page_preview": True,
        }
        chunks = self.split_message(message)
        attempts = 0
        last_error: Optional[str] = None

        for part in chunks:
            delivered = False
            for attempt in range(1, self.settings.telegram_max_retries + 1):
                attempts += 1
                try:
                    response = self.transport(part, payload)
                    status_code = int(response.get("status_code", 200))
                    if status_code == 429:
                        raise TelegramDeliveryError("telegram rate limit")
                    if status_code >= 400:
                        raise TelegramDeliveryError(str(response.get("body") or f"telegram http {status_code}"))
                    delivered = True
                    break
                except Exception as exc:
                    last_error = str(exc)
                    if attempt >= self.settings.telegram_max_retries:
                        break
                    self.sleep(min(0.05 * attempt, 0.2))
            if not delivered:
                return {"status": "FAILED", "attempts": attempts, "error": last_error, "parts": len(chunks)}

        return {"status": "DELIVERED", "attempts": attempts, "error": None, "parts": len(chunks)}

    def _default_transport(self, message: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps({**payload, "text": message}).encode("utf-8")
        request = urllib.request.Request(
            url=f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.telegram_timeout_seconds) as response:  # noqa: S310
            response_body = response.read().decode("utf-8")
            return {"status_code": response.status, "body": response_body}
