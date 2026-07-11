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
    opening_capital: float = 500_000.0
    enable_notifications: bool = True
    status_notification_interval_minutes: int = 5
    status_send_unchanged: bool = True
    status_include_recent_closed: bool = True
    status_recent_closed_window_minutes: int = 10
    enable_telegram: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_parse_mode: str = "HTML"
    telegram_timeout_seconds: int = 10
    telegram_max_retries: int = 3
    notification_retention_days: int = 0
    enable_nse: bool = True
    enable_bse: bool = True
    enable_fno: bool = True
    instrument_import_source: str = "FIXTURE"
    instrument_import_path: str = ""
    instrument_master_max_age_hours: int = 24
    broker_mapping_max_age_hours: int = 24
    quote_fresh_seconds: int = 10
    quote_aging_seconds: int = 30
    max_quote_age_seconds: int = 60
    min_intraday_traded_value: float = 10_000_000.0
    min_btst_traded_value: float = 5_000_000.0
    min_swing_traded_value: float = 1_000_000.0
    max_allowed_spread_pct: float = 0.50
    min_option_oi: int = 1000
    min_option_volume: int = 100

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
        opening_capital=float(merged.get("OPENING_CAPITAL") or 500_000.0),
        enable_notifications=str(merged.get("ENABLE_NOTIFICATIONS") or "true").strip().lower() in {"1", "true", "yes", "on"},
        status_notification_interval_minutes=int(merged.get("STATUS_NOTIFICATION_INTERVAL_MINUTES") or 5),
        status_send_unchanged=str(merged.get("STATUS_SEND_UNCHANGED") or "true").strip().lower() in {"1", "true", "yes", "on"},
        status_include_recent_closed=str(merged.get("STATUS_INCLUDE_RECENT_CLOSED") or "true").strip().lower() in {"1", "true", "yes", "on"},
        status_recent_closed_window_minutes=int(merged.get("STATUS_RECENT_CLOSED_WINDOW_MINUTES") or 10),
        enable_telegram=str(merged.get("ENABLE_TELEGRAM") or "false").strip().lower() in {"1", "true", "yes", "on"},
        telegram_bot_token=(merged.get("TELEGRAM_BOT_TOKEN") or "").strip(),
        telegram_chat_id=(merged.get("TELEGRAM_CHAT_ID") or "").strip(),
        telegram_parse_mode=(merged.get("TELEGRAM_PARSE_MODE") or "HTML").strip().upper(),
        telegram_timeout_seconds=int(merged.get("TELEGRAM_TIMEOUT_SECONDS") or 10),
        telegram_max_retries=int(merged.get("TELEGRAM_MAX_RETRIES") or 3),
        notification_retention_days=int(merged.get("NOTIFICATION_RETENTION_DAYS") or 0),
        enable_nse=str(merged.get("ENABLE_NSE") or "true").strip().lower() in {"1", "true", "yes", "on"},
        enable_bse=str(merged.get("ENABLE_BSE") or "true").strip().lower() in {"1", "true", "yes", "on"},
        enable_fno=str(merged.get("ENABLE_FNO") or "true").strip().lower() in {"1", "true", "yes", "on"},
        instrument_import_source=(merged.get("INSTRUMENT_IMPORT_SOURCE") or "FIXTURE").strip().upper(),
        instrument_import_path=(merged.get("INSTRUMENT_IMPORT_PATH") or "").strip(),
        instrument_master_max_age_hours=int(merged.get("INSTRUMENT_MASTER_MAX_AGE_HOURS") or 24),
        broker_mapping_max_age_hours=int(merged.get("BROKER_MAPPING_MAX_AGE_HOURS") or 24),
        quote_fresh_seconds=int(merged.get("QUOTE_FRESH_SECONDS") or 10),
        quote_aging_seconds=int(merged.get("QUOTE_AGING_SECONDS") or 30),
        max_quote_age_seconds=int(merged.get("MAX_QUOTE_AGE_SECONDS") or 60),
        min_intraday_traded_value=float(merged.get("MIN_INTRADAY_TRADED_VALUE") or 10_000_000.0),
        min_btst_traded_value=float(merged.get("MIN_BTST_TRADED_VALUE") or 5_000_000.0),
        min_swing_traded_value=float(merged.get("MIN_SWING_TRADED_VALUE") or 1_000_000.0),
        max_allowed_spread_pct=float(merged.get("MAX_ALLOWED_SPREAD_PCT") or 0.50),
        min_option_oi=int(merged.get("MIN_OPTION_OI") or 1000),
        min_option_volume=int(merged.get("MIN_OPTION_VOLUME") or 100),
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
    if settings.opening_capital <= 0:
        raise SettingsValidationError("opening capital must be positive")
    if settings.status_notification_interval_minutes <= 0 or settings.status_recent_closed_window_minutes < 0:
        raise SettingsValidationError("invalid notification interval or recent-closed window")
    if settings.telegram_timeout_seconds <= 0 or settings.telegram_max_retries <= 0:
        raise SettingsValidationError("invalid telegram timeout or retry configuration")
    if settings.instrument_master_max_age_hours <= 0 or settings.broker_mapping_max_age_hours <= 0:
        raise SettingsValidationError("invalid instrument master or broker mapping max age")
    if settings.quote_fresh_seconds <= 0 or settings.quote_aging_seconds <= 0 or settings.max_quote_age_seconds <= 0:
        raise SettingsValidationError("invalid quote freshness configuration")
    if settings.quote_fresh_seconds >= settings.quote_aging_seconds or settings.quote_aging_seconds >= settings.max_quote_age_seconds:
        raise SettingsValidationError("quote freshness thresholds must increase strictly")
    if settings.min_intraday_traded_value <= 0 or settings.min_btst_traded_value <= 0 or settings.min_swing_traded_value <= 0:
        raise SettingsValidationError("invalid traded-value threshold")
    if settings.max_allowed_spread_pct <= 0:
        raise SettingsValidationError("invalid spread threshold")
    if settings.min_option_oi < 0 or settings.min_option_volume < 0:
        raise SettingsValidationError("invalid option liquidity threshold")
