from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.database.connection import DatabaseConnection


class Repository:
    def __init__(self, database: DatabaseConnection) -> None:
        self.database = database

    def initialize_schema(self) -> None:
        conn = self.database.connect()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS application_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS broker_readiness (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS idempotency_records (
                idempotency_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reconciliation_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reason TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS health_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

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

            CREATE TABLE IF NOT EXISTS market_data_connections (
                source TEXT PRIMARY KEY,
                connection_state TEXT NOT NULL,
                data_state TEXT NOT NULL,
                readiness_json TEXT NOT NULL,
                last_connected_at TEXT,
                last_updated TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_data_subscriptions (
                subscription_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                source TEXT NOT NULL,
                broker_symbol TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                subscribed_at TEXT,
                status TEXT NOT NULL,
                consumer TEXT NOT NULL,
                timeframes_json TEXT NOT NULL,
                last_tick_at TEXT,
                retry_count INTEGER NOT NULL,
                last_error TEXT,
                consumer_count INTEGER NOT NULL,
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_ticks (
                tick_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                exchange TEXT NOT NULL,
                segment TEXT NOT NULL,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                data_mode TEXT NOT NULL,
                timestamp_exchange TEXT NOT NULL,
                timestamp_received TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                sequence_number INTEGER,
                ltp REAL,
                last_quantity INTEGER,
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
                upper_circuit REAL,
                lower_circuit REAL,
                market_status TEXT,
                raw_reference_json TEXT NOT NULL,
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE,
                FOREIGN KEY(company_id) REFERENCES companies(company_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_tick_rejections (
                rejection_id TEXT PRIMARY KEY,
                tick_id TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                source TEXT NOT NULL,
                rejection_state TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_data_sequences (
                source TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                sequence_number INTEGER,
                timestamp_utc TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(source, instrument_id),
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_data_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_data_reconnects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                delay_seconds REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS latest_quotes (
                instrument_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                ltp REAL,
                bid REAL,
                ask REAL,
                volume INTEGER,
                traded_value REAL,
                data_mode TEXT NOT NULL,
                sequence_number INTEGER,
                payload_json TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_candles (
                candle_id TEXT PRIMARY KEY,
                instrument_id TEXT NOT NULL,
                source TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                traded_value REAL NOT NULL,
                vwap REAL NOT NULL,
                open_interest REAL NOT NULL,
                tick_count INTEGER NOT NULL,
                complete INTEGER NOT NULL,
                data_mode TEXT NOT NULL,
                FOREIGN KEY(instrument_id) REFERENCES instruments(instrument_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_data_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                severity TEXT NOT NULL,
                instrument_id TEXT,
                symbol TEXT,
                reason TEXT,
                action_taken TEXT,
                detected_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decision_timeline (
                timeline_id TEXT PRIMARY KEY,
                correlation_id TEXT,
                trade_id TEXT,
                candidate_id TEXT,
                instrument_id TEXT,
                timestamp_utc TEXT NOT NULL,
                timestamp_ist TEXT NOT NULL,
                module TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_value_json TEXT NOT NULL,
                new_value_json TEXT NOT NULL,
                reason TEXT,
                metrics_json TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_market_ticks_instrument_id ON market_ticks(instrument_id);
            CREATE INDEX IF NOT EXISTS idx_market_ticks_source ON market_ticks(source);
            CREATE INDEX IF NOT EXISTS idx_market_ticks_timestamp_utc ON market_ticks(timestamp_utc);
            CREATE INDEX IF NOT EXISTS idx_market_ticks_timestamp_ist ON market_ticks(timestamp_ist);
            CREATE INDEX IF NOT EXISTS idx_market_ticks_sequence ON market_ticks(sequence_number);
            CREATE INDEX IF NOT EXISTS idx_market_ticks_data_mode ON market_ticks(data_mode);
            CREATE INDEX IF NOT EXISTS idx_market_subscriptions_status ON market_data_subscriptions(status);
            CREATE INDEX IF NOT EXISTS idx_market_subscriptions_last_tick_at ON market_data_subscriptions(last_tick_at);
            CREATE INDEX IF NOT EXISTS idx_market_candles_timeframe ON market_candles(timeframe);
            CREATE INDEX IF NOT EXISTS idx_market_candles_start_time ON market_candles(start_time);
            CREATE INDEX IF NOT EXISTS idx_market_rejections_timestamp ON market_tick_rejections(timestamp_utc);
            CREATE INDEX IF NOT EXISTS idx_market_events_detected_at ON market_data_events(detected_at);
            CREATE INDEX IF NOT EXISTS idx_decision_timeline_instrument_id ON decision_timeline(instrument_id);
            CREATE INDEX IF NOT EXISTS idx_decision_timeline_event_type ON decision_timeline(event_type);
            CREATE INDEX IF NOT EXISTS idx_decision_timeline_timestamp_utc ON decision_timeline(timestamp_utc);
            """
        )

    def _json(self, value: Any) -> str:
        return json.dumps(value)

    def _notification_from_row(self, row: Any) -> Dict[str, Any]:
        data = dict(row)
        data["delivery_channels"] = json.loads(data["delivery_channels"])
        data["payload_json"] = json.loads(data["payload_json"])
        return data

    def save_state(self, key: str, value: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute(
            "INSERT INTO application_state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, self._json(value)),
        )

    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        row = self.database.connect().execute("SELECT value FROM application_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def save_lifecycle_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.database.connect().execute(
            "INSERT INTO lifecycle_events(event_type, payload) VALUES(?, ?)",
            (event_type, self._json(payload)),
        )

    def save_idempotency(self, key: str, payload: Dict[str, Any]) -> None:
        self.database.connect().execute(
            "INSERT INTO idempotency_records(idempotency_key, payload) VALUES(?, ?) ON CONFLICT(idempotency_key) DO UPDATE SET payload=excluded.payload",
            (key, self._json(payload)),
        )

    def save_reconciliation(self, reason: str, payload: Dict[str, Any]) -> None:
        self.database.connect().execute(
            "INSERT INTO reconciliation_records(reason, payload) VALUES(?, ?)",
            (reason, self._json(payload)),
        )

    def save_order(self, payload: Dict[str, Any]) -> None:
        self.database.connect().execute("INSERT INTO orders(payload) VALUES(?)", (self._json(payload),))

    def save_position(self, payload: Dict[str, Any]) -> None:
        self.database.connect().execute("INSERT INTO positions(payload) VALUES(?)", (self._json(payload),))

    def save_system_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        self.database.connect().execute(
            "INSERT INTO system_events(event_type, payload) VALUES(?, ?)",
            (event_type, self._json(payload)),
        )

    def save_health_snapshot(self, status: str, payload: Dict[str, Any]) -> None:
        self.database.connect().execute(
            "INSERT INTO health_snapshots(status, payload) VALUES(?, ?)",
            (status, self._json(payload)),
        )

    def list_orders(self) -> List[Dict[str, Any]]:
        rows = self.database.connect().execute("SELECT payload FROM orders ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]

    def save_notification(self, notification: Dict[str, Any]) -> None:
        conn = self.database.connect()
        conn.execute(
            """
            INSERT INTO notifications(
                notification_id, notification_type, severity, timestamp_utc, timestamp_ist, correlation_id, trade_id,
                order_id, broker_order_id, strategy, symbol, underlying, exchange, instrument_type, option_type, strike,
                expiry, side, quantity, lots, title, summary, reason, event_source, entry_price, current_price, exit_price,
                initial_stop, current_stop, t1, t2, t3, stretch_target, next_predicted_target, t1_status, t2_status,
                t3_status, highest_price, highest_profit, locked_profit, mfe, mae, hold_duration_seconds, trade_pnl,
                trade_pnl_pct, day_realized_pnl, day_unrealized_pnl, day_total_pnl, capital_used_trade, capital_reserved,
                capital_released, capital_used_day, capital_available, account_equity, position_status, order_status,
                execution_mode, configured_primary_broker, active_execution_broker, standby_broker, delivery_channels,
                delivery_status, delivery_attempts, delivery_error, payload_json, created_at, updated_at
            ) VALUES(
                :notification_id, :notification_type, :severity, :timestamp_utc, :timestamp_ist, :correlation_id, :trade_id,
                :order_id, :broker_order_id, :strategy, :symbol, :underlying, :exchange, :instrument_type, :option_type, :strike,
                :expiry, :side, :quantity, :lots, :title, :summary, :reason, :event_source, :entry_price, :current_price, :exit_price,
                :initial_stop, :current_stop, :t1, :t2, :t3, :stretch_target, :next_predicted_target, :t1_status, :t2_status,
                :t3_status, :highest_price, :highest_profit, :locked_profit, :mfe, :mae, :hold_duration_seconds, :trade_pnl,
                :trade_pnl_pct, :day_realized_pnl, :day_unrealized_pnl, :day_total_pnl, :capital_used_trade, :capital_reserved,
                :capital_released, :capital_used_day, :capital_available, :account_equity, :position_status, :order_status,
                :execution_mode, :configured_primary_broker, :active_execution_broker, :standby_broker, :delivery_channels,
                :delivery_status, :delivery_attempts, :delivery_error, :payload_json, :created_at, :updated_at
            )
            """,
            {
                **notification,
                "delivery_channels": self._json(notification.get("delivery_channels", [])),
                "payload_json": self._json(notification.get("payload_json", {})),
            },
        )

    def update_notification_delivery(
        self,
        *,
        notification_id: str,
        delivery_status: str,
        delivery_attempts: int,
        delivery_error: Optional[str],
        delivery_channels: List[str],
    ) -> None:
        self.database.connect().execute(
            """
            UPDATE notifications
            SET delivery_status = ?, delivery_attempts = ?, delivery_error = ?, delivery_channels = ?, updated_at = CURRENT_TIMESTAMP
            WHERE notification_id = ?
            """,
            (delivery_status, delivery_attempts, delivery_error, self._json(delivery_channels), notification_id),
        )

    def save_notification_delivery_attempt(
        self,
        *,
        notification_id: str,
        channel: str,
        status: str,
        attempt_number: int,
        error: Optional[str],
        response: Dict[str, Any],
    ) -> None:
        self.database.connect().execute(
            """
            INSERT INTO notification_delivery_attempts(notification_id, channel, status, attempt_number, error, response_json)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (notification_id, channel, status, attempt_number, error, self._json(response)),
        )

    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        row = self.database.connect().execute(
            "SELECT * FROM notifications WHERE notification_id = ?",
            (notification_id,),
        ).fetchone()
        if row is None:
            return None
        return self._notification_from_row(row)

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
        conditions: List[str] = []
        params: List[Any] = []
        if notification_type:
            conditions.append("notification_type = ?")
            params.append(notification_type)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if symbol:
            conditions.append("symbol = ?")
            params.append(symbol)
        if trade_id:
            conditions.append("trade_id = ?")
            params.append(trade_id)
        if start_time:
            conditions.append("timestamp_utc >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp_utc <= ?")
            params.append(end_time)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.database.connect().execute(
            f"SELECT * FROM notifications {where_clause} ORDER BY timestamp_utc DESC LIMIT ?",
            (*params, max(limit, 1)),
        ).fetchall()
        return [self._notification_from_row(row) for row in rows]

    def save_account_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.database.connect().execute(
            """
            INSERT INTO account_snapshots(
                timestamp_utc, timestamp_ist, opening_capital, account_equity, capital_used_day, capital_reserved,
                capital_available, realized_pnl, unrealized_pnl, total_day_pnl, wins, losses, open_trades, closed_trades,
                execution_mode, configured_primary_broker, active_execution_broker, standby_broker, snapshot_reason, payload_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["timestamp_utc"],
                snapshot["timestamp_ist"],
                snapshot["opening_capital"],
                snapshot["account_equity"],
                snapshot["capital_used_day"],
                snapshot["capital_reserved"],
                snapshot["capital_available"],
                snapshot["realized_pnl"],
                snapshot["unrealized_pnl"],
                snapshot["total_day_pnl"],
                snapshot["wins"],
                snapshot["losses"],
                snapshot["open_trades"],
                snapshot["closed_trades"],
                snapshot["execution_mode"],
                snapshot["configured_primary_broker"],
                snapshot["active_execution_broker"],
                snapshot["standby_broker"],
                snapshot["snapshot_reason"],
                self._json(snapshot),
            ),
        )

    def save_position_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.database.connect().execute(
            """
            INSERT INTO position_snapshots(trade_id, symbol, position_status, timestamp_utc, timestamp_ist, payload_json)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["trade_id"],
                snapshot["symbol"],
                snapshot["position_status"],
                snapshot["timestamp_utc"],
                snapshot["timestamp_ist"],
                self._json(snapshot),
            ),
        )

    def save_trade_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.database.connect().execute(
            """
            INSERT INTO trade_snapshots(trade_id, symbol, status, timestamp_utc, timestamp_ist, payload_json)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["trade_id"],
                snapshot["symbol"],
                snapshot["status"],
                snapshot["timestamp_utc"],
                snapshot["timestamp_ist"],
                self._json(snapshot),
            ),
        )

    def save_day_summary(self, summary: Dict[str, Any]) -> None:
        self.database.connect().execute(
            """
            INSERT INTO day_summaries(summary_date_ist, timestamp_utc, timestamp_ist, total_day_pnl, capital_available, payload_json)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                summary["summary_date_ist"],
                summary["timestamp_utc"],
                summary["timestamp_ist"],
                summary["total_day_pnl"],
                summary["capital_available"],
                self._json(summary),
            ),
        )

    def latest_account_snapshot(self) -> Optional[Dict[str, Any]]:
        row = self.database.connect().execute(
            "SELECT payload_json FROM account_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return json.loads(row[0]) if row else None

    def latest_day_summary(self) -> Optional[Dict[str, Any]]:
        row = self.database.connect().execute(
            "SELECT payload_json FROM day_summaries ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list_delivery_attempts(self, notification_id: str) -> List[Dict[str, Any]]:
        rows = self.database.connect().execute(
            "SELECT * FROM notification_delivery_attempts WHERE notification_id = ? ORDER BY id",
            (notification_id,),
        ).fetchall()
        return [
            {**dict(row), "response_json": json.loads(row["response_json"])}
            for row in rows
        ]

    def save_decision_timeline(self, entry: Dict[str, Any]) -> None:
        self.database.connect().execute(
            """
            INSERT INTO decision_timeline(
                timeline_id, correlation_id, trade_id, candidate_id, instrument_id, timestamp_utc, timestamp_ist, module,
                event_type, previous_value_json, new_value_json, reason, metrics_json, source, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["timeline_id"],
                entry.get("correlation_id"),
                entry.get("trade_id"),
                entry.get("candidate_id"),
                entry.get("instrument_id"),
                entry["timestamp_utc"],
                entry["timestamp_ist"],
                entry["module"],
                entry["event_type"],
                self._json(entry.get("previous_value_json", {})),
                self._json(entry.get("new_value_json", {})),
                entry.get("reason"),
                self._json(entry.get("metrics_json", {})),
                entry["source"],
                entry["created_at"],
            ),
        )

    def list_decision_timeline(
        self,
        *,
        trade_id: Optional[str] = None,
        candidate_id: Optional[str] = None,
        instrument_id: Optional[str] = None,
        module: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if trade_id:
            conditions.append("trade_id = ?")
            params.append(trade_id)
        if candidate_id:
            conditions.append("candidate_id = ?")
            params.append(candidate_id)
        if instrument_id:
            conditions.append("instrument_id = ?")
            params.append(instrument_id)
        if module:
            conditions.append("module = ?")
            params.append(module)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if start_time:
            conditions.append("timestamp_utc >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp_utc <= ?")
            params.append(end_time)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self.database.connect().execute(
            f"SELECT * FROM decision_timeline {where} ORDER BY timestamp_utc DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [
            {
                **dict(row),
                "previous_value_json": json.loads(row["previous_value_json"] or "{}"),
                "new_value_json": json.loads(row["new_value_json"] or "{}"),
                "metrics_json": json.loads(row["metrics_json"] or "{}"),
            }
            for row in rows
        ]
