from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class SettingsValidationError(ValueError):
    pass

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    primary_broker: str = "fyers"
    standby_broker: str = "dhan"
    trading_mode: str = "paper"
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    broker_pin: str = ""
    database_path: str = "data/market_move.db"
    log_level: str = "INFO"
    log_max_bytes: int = 5_242_880
    log_backup_count: int = 5
    timezone: str = "Asia/Kolkata"
    premarket_start_time: str = "08:45"
    market_open_time: str = "09:15"
    market_close_time: str = "15:30"
    post_market_end_time: str = "18:00"
    forced_test_mode: bool = False
    holiday_calendar_path: str = ""

    @property
    def is_paper_mode(self) -> bool:
        return self.trading_mode.lower() == "paper"


def load_settings(env_path: Optional[os.PathLike[str] | str | Path] = None) -> Settings:
    env_file = Path(env_path) if env_path is not None else None
    values = dotenv_values(env_file) if env_file else {}

    if env_file is not None and not env_file.exists():
        values = {}

    merged = {**os.environ, **values}

    return Settings(
        primary_broker=(merged.get("PRIMARY_BROKER") or "fyers").strip().lower(),
        standby_broker=(merged.get("STANDBY_BROKER") or "dhan").strip().lower(),
        trading_mode=(merged.get("TRADING_MODE") or "paper").strip().lower(),
        api_key=(merged.get("BROKER_API_KEY") or "").strip(),
        api_secret=(merged.get("BROKER_SECRET_KEY") or "").strip(),
        access_token=(merged.get("BROKER_ACCESS_TOKEN") or "").strip(),
        broker_pin=(merged.get("BROKER_PIN") or "").strip(),
        database_path=(merged.get("DATABASE_PATH") or "data/market_move.db").strip(),
        log_level=(merged.get("LOG_LEVEL") or "INFO").strip().upper(),
        log_max_bytes=int(merged.get("LOG_MAX_BYTES") or 5_242_880),
        log_backup_count=int(merged.get("LOG_BACKUP_COUNT") or 5),
        timezone=(merged.get("TIMEZONE") or "Asia/Kolkata").strip(),
        premarket_start_time=(merged.get("PREMARKET_START_TIME") or "08:45").strip(),
        market_open_time=(merged.get("MARKET_OPEN_TIME") or "09:15").strip(),
        market_close_time=(merged.get("MARKET_CLOSE_TIME") or "15:30").strip(),
        post_market_end_time=(merged.get("POST_MARKET_END_TIME") or "18:00").strip(),
        forced_test_mode=str(merged.get("FORCED_TEST_MODE") or "false").strip().lower() in {"1", "true", "yes", "on"},
        holiday_calendar_path=(merged.get("HOLIDAY_CALENDAR_PATH") or "").strip(),
    )


def validate_settings(settings: Settings) -> None:
    if not settings.database_path:
        raise SettingsValidationError("database_path is required")

    try:
        from datetime import datetime

        for value in [settings.premarket_start_time, settings.market_open_time, settings.market_close_time, settings.post_market_end_time]:
            datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise SettingsValidationError("invalid time value") from exc

    try:
        import zoneinfo

        zoneinfo.ZoneInfo(settings.timezone)
    except Exception as exc:
        raise SettingsValidationError("unsupported timezone") from exc

    if settings.log_max_bytes <= 0 or settings.log_backup_count <= 0:
        raise SettingsValidationError("invalid log size or backup count")
