from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.database.connection import DatabaseConnection


class MigrationRunner:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database
        self._migrations: List[tuple[str, str]] = [
            (
                "001_initial_schema",
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """,
            ),
            (
                "002_notification_telemetry",
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    notification_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    correlation_id TEXT,
                    trade_id TEXT,
                    order_id TEXT,
                    broker_order_id TEXT,
                    strategy TEXT,
                    symbol TEXT,
                    underlying TEXT,
                    exchange TEXT,
                    instrument_type TEXT,
                    option_type TEXT,
                    strike REAL,
                    expiry TEXT,
                    side TEXT,
                    quantity INTEGER,
                    lots INTEGER,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    reason TEXT,
                    event_source TEXT,
                    entry_price REAL,
                    current_price REAL,
                    exit_price REAL,
                    initial_stop REAL,
                    current_stop REAL,
                    t1 REAL,
                    t2 REAL,
                    t3 REAL,
                    stretch_target REAL,
                    next_predicted_target REAL,
                    t1_status TEXT,
                    t2_status TEXT,
                    t3_status TEXT,
                    highest_price REAL,
                    highest_profit REAL,
                    locked_profit REAL,
                    mfe REAL,
                    mae REAL,
                    hold_duration_seconds INTEGER,
                    trade_pnl REAL,
                    trade_pnl_pct REAL,
                    day_realized_pnl REAL,
                    day_unrealized_pnl REAL,
                    day_total_pnl REAL,
                    capital_used_trade REAL,
                    capital_reserved REAL,
                    capital_released REAL,
                    capital_used_day REAL,
                    capital_available REAL,
                    account_equity REAL,
                    position_status TEXT,
                    order_status TEXT,
                    execution_mode TEXT,
                    configured_primary_broker TEXT,
                    active_execution_broker TEXT,
                    standby_broker TEXT,
                    delivery_channels TEXT NOT NULL,
                    delivery_status TEXT NOT NULL,
                    delivery_attempts INTEGER NOT NULL DEFAULT 0,
                    delivery_error TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notification_delivery_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notification_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    error TEXT,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(notification_id) REFERENCES notifications(notification_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS account_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    opening_capital REAL NOT NULL,
                    account_equity REAL NOT NULL,
                    capital_used_day REAL NOT NULL,
                    capital_reserved REAL NOT NULL,
                    capital_available REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    total_day_pnl REAL NOT NULL,
                    wins INTEGER NOT NULL,
                    losses INTEGER NOT NULL,
                    open_trades INTEGER NOT NULL,
                    closed_trades INTEGER NOT NULL,
                    execution_mode TEXT NOT NULL,
                    configured_primary_broker TEXT NOT NULL,
                    active_execution_broker TEXT NOT NULL,
                    standby_broker TEXT NOT NULL,
                    snapshot_reason TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS position_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    position_status TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS trade_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS day_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary_date_ist TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    total_day_pnl REAL NOT NULL,
                    capital_available REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_notifications_timestamp_ist ON notifications(timestamp_ist);
                CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
                CREATE INDEX IF NOT EXISTS idx_notifications_trade_id ON notifications(trade_id);
                CREATE INDEX IF NOT EXISTS idx_notifications_order_id ON notifications(order_id);
                CREATE INDEX IF NOT EXISTS idx_notifications_symbol ON notifications(symbol);
                CREATE INDEX IF NOT EXISTS idx_notifications_severity ON notifications(severity);
                CREATE INDEX IF NOT EXISTS idx_notifications_delivery_status ON notifications(delivery_status);
                """,
            ),
        ]

    def current_version(self) -> Optional[str]:
        conn = self.database.connect()
        row = conn.execute("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1").fetchone()
        return row[0] if row else None

    def apply(self) -> str:
        conn = self.database.connect()
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        for version, sql in self._migrations:
            existing = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,)).fetchone()
            if existing:
                continue
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
        return self.current_version() or "000"
