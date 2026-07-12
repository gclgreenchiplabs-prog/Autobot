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
    execution_broker: str = "fyers"
    option_chain_broker: str = "dhan"
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    broker_pin: str = ""
    fyers_configured: bool = False
    fyers_client_id: str = ""
    fyers_secret_key: str = ""
    fyers_redirect_uri: str = ""
    fyers_access_token: str = ""
    fyers_execution_enable: bool = False
    dhan_configured: bool = False
    dhan_client_id: str = ""
    dhan_access_token: str = ""
    dhan_execution_enable: bool = False
    dhan_option_chain_enable: bool = False
    dhan_static_ip_ready: bool = False
    dhan_order_api_enable: bool = False
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
    live_order_enable: bool = False
    live_market_data_enable: bool = False
    explicit_live_confirmation: bool = False
    enable_market_data: bool = True
    market_data_mode: str = "FIXTURE"
    primary_market_data_broker: str = "fyers"
    standby_market_data_broker: str = "dhan"
    enable_market_data_failover: bool = False
    enable_execution_failover: bool = False
    failover_requires_manual_approval: bool = True
    fyers_market_data_enable: bool = False
    dhan_market_data_enable: bool = False
    market_data_heartbeat_seconds: int = 5
    market_data_stale_seconds: int = 15
    market_data_failed_seconds: int = 60
    market_data_reconnect_initial_seconds: int = 2
    market_data_reconnect_max_seconds: int = 60
    market_data_max_reconnect_attempts: int = 10
    market_data_reconnect_jitter_seconds: float = 0.0
    market_tick_retention_days: int = 0
    market_candle_retention_days: int = 0
    enable_1m_candles: bool = True
    enable_5m_candles: bool = True
    enable_15m_candles: bool = True
    enable_30m_candles: bool = True
    enable_daily_candles: bool = True
    fixture_market_data_path: str = ""
    fixture_tick_interval_ms: int = 1000
    fixture_auto_start: bool = False

    @property
    def is_paper_mode(self) -> bool:
        return self.trading_mode.lower() == "paper"


def load_settings(env_path: Optional[os.PathLike[str] | str | Path] = None) -> Settings:
    env_file = Path(env_path) if env_path is not None else None
    values = dotenv_values(env_file) if env_file else {}

    if env_file is not None and not env_file.exists():
        values = {}

    merged = {**os.environ, **values}

    def _value(*keys: str, default: str = "") -> str:
        for key in keys:
            value = merged.get(key)
            if value is not None and str(value).strip() != "":
                return str(value)
        return default

    def _bool(*keys: str, default: str = "false") -> bool:
        return _value(*keys, default=default).strip().lower() in {"1", "true", "yes", "on"}

    return Settings(
        primary_broker=_value("PRIMARY_BROKER", default="fyers").strip().lower(),
        standby_broker=_value("STANDBY_BROKER", default="dhan").strip().lower(),
        trading_mode=_value("EXECUTION_MODE", "TRADING_MODE", default="paper").strip().lower(),
        execution_broker=_value("EXECUTION_BROKER", "PRIMARY_BROKER", default="fyers").strip().lower(),
        option_chain_broker=_value("OPTION_CHAIN_BROKER", "STANDBY_MARKET_DATA_BROKER", default="dhan").strip().lower(),
        api_key=_value("BROKER_API_KEY", "FYERS_CLIENT_ID").strip(),
        api_secret=_value("BROKER_SECRET_KEY", "FYERS_SECRET_KEY").strip(),
        access_token=_value("BROKER_ACCESS_TOKEN", "FYERS_ACCESS_TOKEN").strip(),
        broker_pin=_value("BROKER_PIN").strip(),
        fyers_configured=_bool("FYERS_CONFIGURED"),
        fyers_client_id=_value("FYERS_CLIENT_ID").strip(),
        fyers_secret_key=_value("FYERS_SECRET_KEY").strip(),
        fyers_redirect_uri=_value("FYERS_REDIRECT_URI").strip(),
        fyers_access_token=_value("FYERS_ACCESS_TOKEN").strip(),
        fyers_execution_enable=_bool("FYERS_EXECUTION_ENABLE"),
        dhan_configured=_bool("DHAN_CONFIGURED"),
        dhan_client_id=_value("DHAN_CLIENT_ID").strip(),
        dhan_access_token=_value("DHAN_ACCESS_TOKEN").strip(),
        dhan_execution_enable=_bool("DHAN_EXECUTION_ENABLE"),
        dhan_option_chain_enable=_bool("DHAN_OPTION_CHAIN_ENABLE"),
        dhan_static_ip_ready=_bool("DHAN_STATIC_IP_READY"),
        dhan_order_api_enable=_bool("DHAN_ORDER_API_ENABLE"),
        database_path=_value("DATABASE_PATH", default="data/market_move.db").strip(),
        log_level=_value("LOG_LEVEL", default="INFO").strip().upper(),
        log_max_bytes=int(_value("LOG_MAX_BYTES", default="5242880")),
        log_backup_count=int(_value("LOG_BACKUP_COUNT", default="5")),
        timezone=_value("TIMEZONE", default="Asia/Kolkata").strip(),
        premarket_start_time=_value("PREMARKET_START_TIME", default="08:45").strip(),
        market_open_time=_value("MARKET_OPEN_TIME", default="09:15").strip(),
        market_close_time=_value("MARKET_CLOSE_TIME", default="15:30").strip(),
        post_market_end_time=_value("POST_MARKET_END_TIME", default="18:00").strip(),
        forced_test_mode=_bool("FORCED_TEST_MODE"),
        holiday_calendar_path=_value("HOLIDAY_CALENDAR_PATH").strip(),
        opening_capital=float(_value("OPENING_CAPITAL", default="500000")),
        enable_notifications=_bool("ENABLE_NOTIFICATIONS", default="true"),
        status_notification_interval_minutes=int(_value("STATUS_NOTIFICATION_INTERVAL_MINUTES", default="5")),
        status_send_unchanged=_bool("STATUS_SEND_UNCHANGED", default="true"),
        status_include_recent_closed=_bool("STATUS_INCLUDE_RECENT_CLOSED", default="true"),
        status_recent_closed_window_minutes=int(_value("STATUS_RECENT_CLOSED_WINDOW_MINUTES", default="10")),
        enable_telegram=_bool("ENABLE_TELEGRAM"),
        telegram_bot_token=_value("TELEGRAM_BOT_TOKEN").strip(),
        telegram_chat_id=_value("TELEGRAM_CHAT_ID").strip(),
        telegram_parse_mode=_value("TELEGRAM_PARSE_MODE", default="HTML").strip().upper(),
        telegram_timeout_seconds=int(_value("TELEGRAM_TIMEOUT_SECONDS", default="10")),
        telegram_max_retries=int(_value("TELEGRAM_MAX_RETRIES", default="3")),
        notification_retention_days=int(_value("NOTIFICATION_RETENTION_DAYS", default="0")),
        enable_nse=_bool("ENABLE_NSE", default="true"),
        enable_bse=_bool("ENABLE_BSE", default="true"),
        enable_fno=_bool("ENABLE_FNO", default="true"),
        instrument_import_source=_value("INSTRUMENT_IMPORT_SOURCE", default="FIXTURE").strip().upper(),
        instrument_import_path=_value("INSTRUMENT_IMPORT_PATH").strip(),
        instrument_master_max_age_hours=int(_value("INSTRUMENT_MASTER_MAX_AGE_HOURS", default="24")),
        broker_mapping_max_age_hours=int(_value("BROKER_MAPPING_MAX_AGE_HOURS", default="24")),
        quote_fresh_seconds=int(_value("QUOTE_FRESH_SECONDS", default="10")),
        quote_aging_seconds=int(_value("QUOTE_AGING_SECONDS", default="30")),
        max_quote_age_seconds=int(_value("MAX_QUOTE_AGE_SECONDS", default="60")),
        min_intraday_traded_value=float(_value("MIN_INTRADAY_TRADED_VALUE", default="10000000")),
        min_btst_traded_value=float(_value("MIN_BTST_TRADED_VALUE", default="5000000")),
        min_swing_traded_value=float(_value("MIN_SWING_TRADED_VALUE", default="1000000")),
        max_allowed_spread_pct=float(_value("MAX_ALLOWED_SPREAD_PCT", default="0.50")),
        min_option_oi=int(_value("MIN_OPTION_OI", default="1000")),
        min_option_volume=int(_value("MIN_OPTION_VOLUME", default="100")),
        live_order_enable=_bool("LIVE_ORDER_ENABLE"),
        live_market_data_enable=_bool("LIVE_MARKET_DATA_ENABLE"),
        explicit_live_confirmation=_bool("EXPLICIT_LIVE_CONFIRMATION"),
        enable_market_data=_bool("ENABLE_MARKET_DATA", default="true"),
        market_data_mode=_value("MARKET_DATA_MODE", default="FIXTURE").strip().upper(),
        primary_market_data_broker=_value("PRIMARY_MARKET_DATA_BROKER", default="FYERS").strip().lower(),
        standby_market_data_broker=_value("STANDBY_MARKET_DATA_BROKER", default="DHAN").strip().lower(),
        enable_market_data_failover=_bool("ENABLE_MARKET_DATA_FAILOVER"),
        enable_execution_failover=_bool("ENABLE_EXECUTION_FAILOVER"),
        failover_requires_manual_approval=_bool("FAILOVER_REQUIRES_MANUAL_APPROVAL", default="true"),
        fyers_market_data_enable=_bool("FYERS_MARKET_DATA_ENABLE"),
        dhan_market_data_enable=_bool("DHAN_MARKET_DATA_ENABLE"),
        market_data_heartbeat_seconds=int(_value("MARKET_DATA_HEARTBEAT_SECONDS", default="5")),
        market_data_stale_seconds=int(_value("MARKET_DATA_STALE_SECONDS", default="15")),
        market_data_failed_seconds=int(_value("MARKET_DATA_FAILED_SECONDS", default="60")),
        market_data_reconnect_initial_seconds=int(_value("MARKET_DATA_RECONNECT_INITIAL_SECONDS", default="2")),
        market_data_reconnect_max_seconds=int(_value("MARKET_DATA_RECONNECT_MAX_SECONDS", default="60")),
        market_data_max_reconnect_attempts=int(_value("MARKET_DATA_MAX_RECONNECT_ATTEMPTS", default="10")),
        market_data_reconnect_jitter_seconds=float(_value("MARKET_DATA_RECONNECT_JITTER_SECONDS", default="0.0")),
        market_tick_retention_days=int(_value("MARKET_TICK_RETENTION_DAYS", default="0")),
        market_candle_retention_days=int(_value("MARKET_CANDLE_RETENTION_DAYS", default="0")),
        enable_1m_candles=_bool("ENABLE_1M_CANDLES", default="true"),
        enable_5m_candles=_bool("ENABLE_5M_CANDLES", default="true"),
        enable_15m_candles=_bool("ENABLE_15M_CANDLES", default="true"),
        enable_30m_candles=_bool("ENABLE_30M_CANDLES", default="true"),
        enable_daily_candles=_bool("ENABLE_DAILY_CANDLES", default="true"),
        fixture_market_data_path=_value("FIXTURE_MARKET_DATA_PATH").strip(),
        fixture_tick_interval_ms=int(_value("FIXTURE_TICK_INTERVAL_MS", default="1000")),
        fixture_auto_start=_bool("FIXTURE_AUTO_START"),
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
    if settings.market_data_mode not in {"FIXTURE", "LIVE", "DELAYED", "HISTORICAL"}:
        raise SettingsValidationError("invalid market data mode")
    if settings.primary_market_data_broker not in {"fyers", "dhan"} or settings.standby_market_data_broker not in {"fyers", "dhan"}:
        raise SettingsValidationError("unsupported market-data broker")
    if settings.primary_broker not in {"fyers", "dhan"} or settings.standby_broker not in {"fyers", "dhan"} or settings.execution_broker not in {"fyers", "dhan"}:
        raise SettingsValidationError("unsupported execution broker")
    if settings.option_chain_broker not in {"fyers", "dhan"}:
        raise SettingsValidationError("unsupported option-chain broker")
    if settings.is_paper_mode and settings.live_order_enable:
        raise SettingsValidationError("live orders cannot be enabled in paper mode")
    if settings.market_data_mode != "LIVE" and settings.live_market_data_enable:
        raise SettingsValidationError("live market-data enable requires MARKET_DATA_MODE=LIVE")
    if settings.market_data_heartbeat_seconds <= 0 or settings.market_data_stale_seconds <= 0 or settings.market_data_failed_seconds <= 0:
        raise SettingsValidationError("invalid market-data timing configuration")
    if settings.market_data_heartbeat_seconds >= settings.market_data_stale_seconds or settings.market_data_stale_seconds >= settings.market_data_failed_seconds:
        raise SettingsValidationError("market-data thresholds must increase strictly")
    if settings.market_data_reconnect_initial_seconds <= 0 or settings.market_data_reconnect_max_seconds <= 0:
        raise SettingsValidationError("invalid market-data reconnect configuration")
    if settings.market_data_reconnect_initial_seconds > settings.market_data_reconnect_max_seconds:
        raise SettingsValidationError("market-data reconnect initial delay cannot exceed max delay")
    if settings.market_data_max_reconnect_attempts < 0 or settings.market_data_reconnect_jitter_seconds < 0:
        raise SettingsValidationError("invalid market-data retry configuration")
    if settings.market_tick_retention_days < 0 or settings.market_candle_retention_days < 0:
        raise SettingsValidationError("invalid market-data retention configuration")
    if settings.fixture_tick_interval_ms <= 0:
        raise SettingsValidationError("invalid fixture tick interval")
    if not any(
        [
            settings.enable_1m_candles,
            settings.enable_5m_candles,
            settings.enable_15m_candles,
            settings.enable_30m_candles,
            settings.enable_daily_candles,
        ]
    ):
        raise SettingsValidationError("at least one candle timeframe must be enabled")
