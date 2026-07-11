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
            (
                "003_instrument_universe",
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    isin TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap_category TEXT,
                    active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS instruments (
                    instrument_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    trading_symbol TEXT NOT NULL,
                    exchange_token TEXT,
                    broker TEXT,
                    broker_symbol TEXT,
                    broker_security_id TEXT,
                    isin TEXT,
                    instrument_type TEXT NOT NULL,
                    underlying_symbol TEXT,
                    expiry TEXT,
                    strike REAL,
                    option_type TEXT,
                    lot_size INTEGER NOT NULL,
                    tick_size REAL NOT NULL,
                    price_precision INTEGER NOT NULL,
                    fno_eligible INTEGER NOT NULL,
                    cash_eligible INTEGER NOT NULL,
                    bse_code TEXT,
                    nse_symbol TEXT,
                    currency TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    listing_date TEXT,
                    delisting_date TEXT,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS broker_instrument_mappings (
                    mapping_id TEXT PRIMARY KEY,
                    instrument_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    broker TEXT NOT NULL,
                    broker_symbol TEXT,
                    broker_security_id TEXT,
                    exchange_token TEXT,
                    trading_symbol TEXT,
                    instrument_type TEXT,
                    expiry TEXT,
                    strike REAL,
                    option_type TEXT,
                    lot_size INTEGER,
                    mapping_status TEXT NOT NULL,
                    last_verified_timestamp TEXT,
                    active INTEGER NOT NULL,
                    conflict_reason TEXT,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE,
                    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS instrument_import_runs (
                    run_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    validation_status TEXT NOT NULL,
                    import_timestamp TEXT NOT NULL,
                    completed_at TEXT,
                    last_successful_refresh TEXT,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS instrument_conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    conflict_type TEXT NOT NULL,
                    symbol TEXT,
                    isin TEXT,
                    brokers_involved TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    resolution_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_quotes (
                    instrument_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    timestamp_ist TEXT NOT NULL,
                    ltp REAL,
                    open REAL,
                    high REAL,
                    low REAL,
                    previous_close REAL,
                    bid REAL,
                    ask REAL,
                    bid_quantity INTEGER,
                    ask_quantity INTEGER,
                    volume INTEGER,
                    traded_value REAL,
                    vwap REAL,
                    open_interest REAL,
                    change_in_oi REAL,
                    data_mode TEXT NOT NULL,
                    sequence_number INTEGER,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS liquidity_snapshots (
                    instrument_id TEXT PRIMARY KEY,
                    quote_timestamp_utc TEXT NOT NULL,
                    liquidity_score INTEGER NOT NULL,
                    liquidity_class TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    eligible_for_intraday INTEGER NOT NULL,
                    eligible_for_btst INTEGER NOT NULL,
                    eligible_for_swing INTEGER NOT NULL,
                    eligible_for_options INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS data_quality_snapshots (
                    instrument_id TEXT PRIMARY KEY,
                    quality_score INTEGER NOT NULL,
                    quality_class TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    staleness_state TEXT NOT NULL,
                    quote_age_seconds REAL,
                    import_age_hours REAL,
                    mapping_age_hours REAL,
                    spread_state TEXT NOT NULL,
                    spread_pct REAL,
                    completeness_score INTEGER NOT NULL,
                    conflict_state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS scanner_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    instrument_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    strategy_scope TEXT NOT NULL,
                    score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    liquidity_score REAL NOT NULL,
                    data_quality_score REAL NOT NULL,
                    fno_eligible INTEGER NOT NULL,
                    preferred_exchange TEXT NOT NULL,
                    data_mode TEXT NOT NULL,
                    eligible INTEGER NOT NULL,
                    rejection_reasons_json TEXT NOT NULL,
                    selection_reasons_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
                    FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_companies_isin ON companies(isin);
                CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);
                CREATE INDEX IF NOT EXISTS idx_instruments_exchange ON instruments(exchange);
                CREATE INDEX IF NOT EXISTS idx_instruments_segment ON instruments(segment);
                CREATE INDEX IF NOT EXISTS idx_instruments_type ON instruments(instrument_type);
                CREATE INDEX IF NOT EXISTS idx_instruments_isin ON instruments(isin);
                CREATE INDEX IF NOT EXISTS idx_instruments_underlying_symbol ON instruments(underlying_symbol);
                CREATE INDEX IF NOT EXISTS idx_instruments_expiry ON instruments(expiry);
                CREATE INDEX IF NOT EXISTS idx_instruments_fno_eligible ON instruments(fno_eligible);
                CREATE INDEX IF NOT EXISTS idx_instruments_active ON instruments(active);
                CREATE INDEX IF NOT EXISTS idx_instruments_last_updated ON instruments(last_updated);
                CREATE INDEX IF NOT EXISTS idx_mapping_broker ON broker_instrument_mappings(broker);
                CREATE INDEX IF NOT EXISTS idx_mapping_broker_symbol ON broker_instrument_mappings(broker_symbol);
                CREATE INDEX IF NOT EXISTS idx_mapping_security_id ON broker_instrument_mappings(broker_security_id);
                CREATE INDEX IF NOT EXISTS idx_quotes_instrument ON market_quotes(instrument_id);
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
