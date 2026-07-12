from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database.repository import Repository
from app.instruments.repository import InstrumentRepository


class MarketDataRepository:
    def __init__(self, repository: Repository, instrument_repository: InstrumentRepository) -> None:
        self.repository = repository
        self.instrument_repository = instrument_repository

    @property
    def _conn(self) -> Any:
        return self.repository.database.connect()

    def list_quality(self, *, quality_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_quality(quality_class=quality_class, limit=limit, offset=offset)

    def list_liquidity(self, *, liquidity_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_liquidity(liquidity_class=liquidity_class, limit=limit, offset=offset)

    def list_staleness(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        return self.instrument_repository.list_staleness(limit=limit, offset=offset)

    def upsert_connection(self, *, source: str, connection_state: str, data_state: str, readiness_json: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO market_data_connections(source, connection_state, data_state, readiness_json, last_connected_at, last_updated)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                connection_state=excluded.connection_state,
                data_state=excluded.data_state,
                readiness_json=excluded.readiness_json,
                last_connected_at=excluded.last_connected_at,
                last_updated=excluded.last_updated
            """,
            (source, connection_state, data_state, json.dumps(readiness_json), now, now),
        )

    def list_connections(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM market_data_connections ORDER BY source").fetchall()
        return [{**dict(row), "readiness_json": json.loads(row["readiness_json"] or "{}")} for row in rows]

    def upsert_subscription(self, subscription: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO market_data_subscriptions(
                subscription_id, instrument_id, source, broker_symbol, requested_at, subscribed_at, status,
                consumer, timeframes_json, last_tick_at, retry_count, last_error, consumer_count
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(subscription_id) DO UPDATE SET
                requested_at=excluded.requested_at,
                subscribed_at=excluded.subscribed_at,
                status=excluded.status,
                consumer=excluded.consumer,
                timeframes_json=excluded.timeframes_json,
                last_tick_at=excluded.last_tick_at,
                retry_count=excluded.retry_count,
                last_error=excluded.last_error,
                consumer_count=excluded.consumer_count
            """,
            (
                subscription["subscription_id"],
                subscription["instrument_id"],
                subscription["source"],
                subscription["broker_symbol"],
                subscription["requested_at"],
                subscription.get("subscribed_at"),
                subscription["status"],
                subscription["consumer"],
                json.dumps(subscription.get("timeframes", [])),
                subscription.get("last_tick_at"),
                subscription.get("retry_count", 0),
                subscription.get("last_error"),
                subscription.get("consumer_count", 1),
            ),
        )

    def list_subscriptions(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM market_data_subscriptions ORDER BY source, instrument_id").fetchall()
        return [{**dict(row), "timeframes": json.loads(row["timeframes_json"] or "[]")} for row in rows]

    def save_tick(self, tick: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO market_ticks(
                tick_id, instrument_id, company_id, exchange, segment, symbol, source, data_mode, timestamp_exchange,
                timestamp_received, timestamp_utc, timestamp_ist, sequence_number, ltp, last_quantity, open, high, low,
                previous_close, bid, ask, bid_quantity, ask_quantity, volume, traded_value, vwap, open_interest,
                change_in_oi, upper_circuit, lower_circuit, market_status, raw_reference_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tick["tick_id"],
                tick["instrument_id"],
                tick["company_id"],
                tick["exchange"],
                tick["segment"],
                tick["symbol"],
                tick["source"],
                tick["data_mode"],
                tick["timestamp_exchange"],
                tick["timestamp_received"],
                tick["timestamp_utc"],
                tick["timestamp_ist"],
                tick.get("sequence_number"),
                tick.get("ltp"),
                tick.get("last_quantity"),
                tick.get("open"),
                tick.get("high"),
                tick.get("low"),
                tick.get("previous_close"),
                tick.get("bid"),
                tick.get("ask"),
                tick.get("bid_quantity"),
                tick.get("ask_quantity"),
                tick.get("volume"),
                tick.get("traded_value"),
                tick.get("vwap"),
                tick.get("open_interest"),
                tick.get("change_in_oi"),
                tick.get("upper_circuit"),
                tick.get("lower_circuit"),
                tick.get("market_status"),
                json.dumps(tick.get("raw_reference", {})),
            ),
        )

    def save_tick_rejection(self, *, tick: Dict[str, Any], rejection_state: str, reasons: List[str]) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO market_tick_rejections(
                rejection_id, tick_id, instrument_id, source, rejection_state, reasons_json, timestamp_utc, payload_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"reject:{tick['tick_id']}:{rejection_state}",
                tick["tick_id"],
                tick["instrument_id"],
                tick["source"],
                rejection_state,
                json.dumps(reasons),
                datetime.now(timezone.utc).isoformat(),
                json.dumps(tick),
            ),
        )

    def list_tick_rejections(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM market_tick_rejections ORDER BY timestamp_utc DESC LIMIT ?", (limit,)).fetchall()
        return [
            {**dict(row), "reasons_json": json.loads(row["reasons_json"] or "[]"), "payload_json": json.loads(row["payload_json"] or "{}")}
            for row in rows
        ]

    def save_sequence(self, *, source: str, instrument_id: str, sequence_number: Optional[int], timestamp_utc: str, fingerprint: str) -> None:
        self._conn.execute(
            """
            INSERT INTO market_data_sequences(source, instrument_id, sequence_number, timestamp_utc, fingerprint, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, instrument_id) DO UPDATE SET
                sequence_number=excluded.sequence_number,
                timestamp_utc=excluded.timestamp_utc,
                fingerprint=excluded.fingerprint,
                updated_at=excluded.updated_at
            """,
            (source, instrument_id, sequence_number, timestamp_utc, fingerprint, datetime.now(timezone.utc).isoformat()),
        )

    def save_heartbeat(self, *, source: str, payload: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO market_data_heartbeats(source, timestamp_utc, payload_json)
            VALUES(?, ?, ?)
            """,
            (source, datetime.now(timezone.utc).isoformat(), json.dumps(payload)),
        )

    def latest_heartbeat(self, *, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if source:
            row = self._conn.execute(
                "SELECT * FROM market_data_heartbeats WHERE source = ? ORDER BY id DESC LIMIT 1",
                (source,),
            ).fetchone()
        else:
            row = self._conn.execute("SELECT * FROM market_data_heartbeats ORDER BY id DESC LIMIT 1").fetchone()
        return {**dict(row), "payload_json": json.loads(row["payload_json"] or "{}")} if row else None

    def save_reconnect(self, *, source: str, attempt: int, delay_seconds: float, status: str) -> None:
        self._conn.execute(
            """
            INSERT INTO market_data_reconnects(source, attempt, delay_seconds, status, timestamp_utc)
            VALUES(?, ?, ?, ?, ?)
            """,
            (source, attempt, delay_seconds, status, datetime.now(timezone.utc).isoformat()),
        )

    def upsert_latest_quote(self, quote: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO latest_quotes(
                instrument_id, source, timestamp_utc, timestamp_ist, ltp, bid, ask, volume, traded_value, data_mode, sequence_number, payload_json, last_updated
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(instrument_id) DO UPDATE SET
                source=excluded.source,
                timestamp_utc=excluded.timestamp_utc,
                timestamp_ist=excluded.timestamp_ist,
                ltp=excluded.ltp,
                bid=excluded.bid,
                ask=excluded.ask,
                volume=excluded.volume,
                traded_value=excluded.traded_value,
                data_mode=excluded.data_mode,
                sequence_number=excluded.sequence_number,
                payload_json=excluded.payload_json,
                last_updated=excluded.last_updated
            """,
            (
                quote["instrument_id"],
                quote["source"],
                quote["timestamp_utc"],
                quote["timestamp_ist"],
                quote.get("ltp"),
                quote.get("bid"),
                quote.get("ask"),
                quote.get("volume"),
                quote.get("traded_value"),
                quote["data_mode"],
                quote.get("sequence_number"),
                json.dumps(quote),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def upsert_quote_projection(self, quote: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO market_quotes(
                instrument_id, source, timestamp_utc, timestamp_ist, ltp, open, high, low, previous_close, bid, ask, bid_quantity,
                ask_quantity, volume, traded_value, vwap, open_interest, change_in_oi, data_mode, sequence_number, received_at
            ) VALUES(
                :instrument_id, :source, :timestamp_utc, :timestamp_ist, :ltp, :open, :high, :low, :previous_close, :bid, :ask, :bid_quantity,
                :ask_quantity, :volume, :traded_value, :vwap, :open_interest, :change_in_oi, :data_mode, :sequence_number, :timestamp_received
            )
            ON CONFLICT(instrument_id) DO UPDATE SET
                source=excluded.source,
                timestamp_utc=excluded.timestamp_utc,
                timestamp_ist=excluded.timestamp_ist,
                ltp=excluded.ltp,
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                previous_close=excluded.previous_close,
                bid=excluded.bid,
                ask=excluded.ask,
                bid_quantity=excluded.bid_quantity,
                ask_quantity=excluded.ask_quantity,
                volume=excluded.volume,
                traded_value=excluded.traded_value,
                vwap=excluded.vwap,
                open_interest=excluded.open_interest,
                change_in_oi=excluded.change_in_oi,
                data_mode=excluded.data_mode,
                sequence_number=excluded.sequence_number,
                received_at=excluded.received_at
            """,
            quote,
        )

    def list_latest_quotes(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM latest_quotes ORDER BY instrument_id").fetchall()
        return [{**dict(row), "payload_json": json.loads(row["payload_json"] or "{}")} for row in rows]

    def save_candle(self, candle: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO market_candles(
                candle_id, instrument_id, source, timeframe, start_time, end_time, open, high, low, close, volume, traded_value,
                vwap, open_interest, tick_count, complete, data_mode
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{candle['instrument_id']}:{candle['source']}:{candle['timeframe']}:{candle['start_time']}",
                candle["instrument_id"],
                candle["source"],
                candle["timeframe"],
                candle["start_time"],
                candle["end_time"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
                candle["traded_value"],
                candle["vwap"],
                candle["open_interest"],
                candle["tick_count"],
                int(candle["complete"]),
                candle["data_mode"],
            ),
        )

    def list_candles(
        self,
        *,
        instrument_id: Optional[str] = None,
        timeframe: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []
        if instrument_id:
            conditions.append("instrument_id = ?")
            params.append(instrument_id)
        if timeframe:
            conditions.append("timeframe = ?")
            params.append(timeframe)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(
            f"SELECT * FROM market_candles {where} ORDER BY start_time DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
        return [{**dict(row), "complete": bool(row["complete"])} for row in rows]

    def save_market_data_event(self, event: Dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO market_data_events(
                event_id, event_type, source, severity, instrument_id, symbol, reason, action_taken, detected_at, payload_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["event_type"],
                event["source"],
                event["severity"],
                event.get("instrument_id"),
                event.get("symbol"),
                event.get("reason"),
                event.get("action_taken"),
                event["detected_at"],
                json.dumps(event),
            ),
        )

    def list_market_data_events(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM market_data_events ORDER BY detected_at DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(row), "payload_json": json.loads(row["payload_json"] or "{}")} for row in rows]
