from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.database.repository import Repository


class InstrumentRepository:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    @property
    def _conn(self) -> Any:
        return self.repository.database.connect()

    def create_import_run(self, *, source: str, source_version: str, checksum: str, row_count: int, metadata: Dict[str, Any]) -> str:
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self._conn.execute(
            """
            INSERT INTO instrument_import_runs(run_id, source, source_version, checksum, row_count, validation_status, import_timestamp, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, source, source_version, checksum, row_count, "RUNNING", datetime.now(timezone.utc).isoformat(), json.dumps(metadata)),
        )
        return run_id

    def complete_import_run(self, run_id: str, *, validation_status: str, metadata: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE instrument_import_runs
            SET validation_status = ?, completed_at = ?, metadata_json = ?, last_successful_refresh = CASE WHEN ? = 'SUCCESS' THEN ? ELSE last_successful_refresh END
            WHERE run_id = ?
            """,
            (validation_status, now, json.dumps(metadata), validation_status, now, run_id),
        )

    def latest_import_run(self) -> Optional[Dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM instrument_import_runs ORDER BY import_timestamp DESC LIMIT 1").fetchone()
        if row is None:
            return None
        data = dict(row)
        data["metadata_json"] = json.loads(data["metadata_json"] or "{}")
        return data

    def atomic_replace(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        run_id = self.create_import_run(
            source=bundle["source"],
            source_version=bundle["source_version"],
            checksum=bundle["checksum"],
            row_count=len(bundle["companies"]) + len(bundle["instruments"]),
            metadata={"started": True},
        )
        conn = self.repository.database.connect()
        try:
            with self.repository.database.transaction() as txn:
                for table in [
                    "companies",
                    "instruments",
                    "broker_instrument_mappings",
                    "instrument_conflicts",
                    "market_quotes",
                    "liquidity_snapshots",
                    "data_quality_snapshots",
                    "scanner_candidates",
                ]:
                    txn.execute(f"DELETE FROM {table}")

                txn.executemany(
                    """
                    INSERT INTO companies(company_id, company_name, isin, sector, industry, market_cap_category, active, created_at, updated_at)
                    VALUES(:company_id, :company_name, :isin, :sector, :industry, :market_cap_category, :active, :created_at, :updated_at)
                    """,
                    bundle["companies"],
                )
                txn.executemany(
                    """
                    INSERT INTO instruments(
                        instrument_id, company_id, exchange, segment, symbol, trading_symbol, exchange_token, broker, broker_symbol, broker_security_id,
                        isin, instrument_type, underlying_symbol, expiry, strike, option_type, lot_size, tick_size, price_precision, fno_eligible,
                        cash_eligible, bse_code, nse_symbol, currency, active, listing_date, delisting_date, last_updated
                    ) VALUES(
                        :instrument_id, :company_id, :exchange, :segment, :symbol, :trading_symbol, :exchange_token, :broker, :broker_symbol, :broker_security_id,
                        :isin, :instrument_type, :underlying_symbol, :expiry, :strike, :option_type, :lot_size, :tick_size, :price_precision, :fno_eligible,
                        :cash_eligible, :bse_code, :nse_symbol, :currency, :active, :listing_date, :delisting_date, :last_updated
                    )
                    """,
                    bundle["instruments"],
                )
                txn.executemany(
                    """
                    INSERT INTO broker_instrument_mappings(
                        mapping_id, instrument_id, company_id, exchange, segment, broker, broker_symbol, broker_security_id, exchange_token,
                        trading_symbol, instrument_type, expiry, strike, option_type, lot_size, mapping_status, last_verified_timestamp, active, conflict_reason
                    ) VALUES(
                        :mapping_id, :instrument_id, :company_id, :exchange, :segment, :broker, :broker_symbol, :broker_security_id, :exchange_token,
                        :trading_symbol, :instrument_type, :expiry, :strike, :option_type, :lot_size, :mapping_status, :last_verified_timestamp, :active, :conflict_reason
                    )
                    """,
                    bundle["mappings"],
                )
                txn.executemany(
                    """
                    INSERT INTO instrument_conflicts(conflict_id, conflict_type, symbol, isin, brokers_involved, reason, resolution_status, payload_json, created_at, updated_at)
                    VALUES(:conflict_id, :conflict_type, :symbol, :isin, :brokers_involved, :reason, :resolution_status, :payload_json, :created_at, :updated_at)
                    """,
                    [
                        {
                            **item,
                            "brokers_involved": json.dumps(item["brokers_involved"]),
                            "payload_json": json.dumps(item["payload_json"]),
                        }
                        for item in bundle["conflicts"]
                    ],
                )
                txn.executemany(
                    """
                    INSERT INTO market_quotes(
                        instrument_id, source, timestamp_utc, timestamp_ist, ltp, open, high, low, previous_close, bid, ask, bid_quantity,
                        ask_quantity, volume, traded_value, vwap, open_interest, change_in_oi, data_mode, sequence_number, received_at
                    ) VALUES(
                        :instrument_id, :source, :timestamp_utc, :timestamp_ist, :ltp, :open, :high, :low, :previous_close, :bid, :ask, :bid_quantity,
                        :ask_quantity, :volume, :traded_value, :vwap, :open_interest, :change_in_oi, :data_mode, :sequence_number, :received_at
                    )
                    """,
                    bundle["quotes"],
                )
                txn.executemany(
                    """
                    INSERT INTO liquidity_snapshots(
                        instrument_id, quote_timestamp_utc, liquidity_score, liquidity_class, reasons_json,
                        eligible_for_intraday, eligible_for_btst, eligible_for_swing, eligible_for_options, created_at
                    ) VALUES(
                        :instrument_id, :quote_timestamp_utc, :liquidity_score, :liquidity_class, :reasons_json,
                        :eligible_for_intraday, :eligible_for_btst, :eligible_for_swing, :eligible_for_options, :created_at
                    )
                    """,
                    [{**item, "reasons_json": json.dumps(item["reasons_json"])} for item in bundle["liquidity"]],
                )
                txn.executemany(
                    """
                    INSERT INTO data_quality_snapshots(
                        instrument_id, quality_score, quality_class, reasons_json, staleness_state, quote_age_seconds, import_age_hours,
                        mapping_age_hours, spread_state, spread_pct, completeness_score, conflict_state, created_at
                    ) VALUES(
                        :instrument_id, :quality_score, :quality_class, :reasons_json, :staleness_state, :quote_age_seconds, :import_age_hours,
                        :mapping_age_hours, :spread_state, :spread_pct, :completeness_score, :conflict_state, :created_at
                    )
                    """,
                    [{**item, "reasons_json": json.dumps(item["reasons_json"])} for item in bundle["quality"]],
                )
                txn.executemany(
                    """
                    INSERT INTO scanner_candidates(
                        candidate_id, company_id, instrument_id, symbol, exchange, direction, instrument_type, strategy_scope, score,
                        confidence, liquidity_score, data_quality_score, fno_eligible, preferred_exchange, data_mode, eligible,
                        rejection_reasons_json, selection_reasons_json, created_at
                    ) VALUES(
                        :candidate_id, :company_id, :instrument_id, :symbol, :exchange, :direction, :instrument_type, :strategy_scope, :score,
                        :confidence, :liquidity_score, :data_quality_score, :fno_eligible, :preferred_exchange, :data_mode, :eligible,
                        :rejection_reasons_json, :selection_reasons_json, :created_at
                    )
                    """,
                    [
                        {
                            **item,
                            "rejection_reasons_json": json.dumps(item["rejection_reasons_json"]),
                            "selection_reasons_json": json.dumps(item["selection_reasons_json"]),
                        }
                        for item in bundle["candidates"]
                    ],
                )

            self.complete_import_run(run_id, validation_status="SUCCESS", metadata={"row_count": len(bundle["instruments"]), "conflict_count": len(bundle["conflicts"])})
        except Exception as exc:
            self.complete_import_run(run_id, validation_status="FAILED", metadata={"error": str(exc)})
            raise
        return self.latest_import_run() or {"run_id": run_id}

    def list_companies(self, *, limit: int = 100, offset: int = 0, exchange: Optional[str] = None, symbol: Optional[str] = None, isin: Optional[str] = None, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if exchange:
            conditions.append("EXISTS (SELECT 1 FROM instruments i WHERE i.company_id = c.company_id AND i.exchange = ?)")
            params.append(exchange)
        if symbol:
            conditions.append("EXISTS (SELECT 1 FROM instruments i WHERE i.company_id = c.company_id AND i.symbol = ?)")
            params.append(symbol)
        if isin:
            conditions.append("c.isin = ?")
            params.append(isin)
        if active is not None:
            conditions.append("c.active = ?")
            params.append(int(active))
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(f"SELECT * FROM companies c {where_clause} ORDER BY c.company_name LIMIT ? OFFSET ?", (*params, limit, offset)).fetchall()
        return [dict(row) for row in rows]

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
        return dict(row) if row else None

    def list_instruments(
        self,
        *,
        exchange: Optional[str] = None,
        segment: Optional[str] = None,
        instrument_type: Optional[str] = None,
        fno_eligible: Optional[bool] = None,
        active: Optional[bool] = None,
        symbol: Optional[str] = None,
        isin: Optional[str] = None,
        broker: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if exchange:
            conditions.append("i.exchange = ?")
            params.append(exchange)
        if segment:
            conditions.append("i.segment = ?")
            params.append(segment)
        if instrument_type:
            conditions.append("i.instrument_type = ?")
            params.append(instrument_type)
        if fno_eligible is not None:
            conditions.append("i.fno_eligible = ?")
            params.append(int(fno_eligible))
        if active is not None:
            conditions.append("i.active = ?")
            params.append(int(active))
        if symbol:
            conditions.append("i.symbol = ?")
            params.append(symbol)
        if isin:
            conditions.append("i.isin = ?")
            params.append(isin)
        if broker:
            conditions.append("EXISTS (SELECT 1 FROM broker_instrument_mappings m WHERE m.instrument_id = i.instrument_id AND m.broker = ?)")
            params.append(broker.lower())
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = self._conn.execute(
            f"""
            SELECT
                i.*,
                c.company_name,
                c.sector,
                c.industry,
                q.data_mode,
                q.timestamp_utc AS quote_timestamp_utc,
                l.liquidity_score,
                l.liquidity_class,
                d.quality_score,
                d.quality_class,
                d.staleness_state
            FROM instruments i
            JOIN companies c ON c.company_id = i.company_id
            LEFT JOIN market_quotes q ON q.instrument_id = i.instrument_id
            LEFT JOIN liquidity_snapshots l ON l.instrument_id = i.instrument_id
            LEFT JOIN data_quality_snapshots d ON d.instrument_id = i.instrument_id
            {where_clause}
            ORDER BY c.company_name, i.exchange, i.segment
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_instrument(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        rows = self.list_instruments(limit=1, offset=0)
        row = self._conn.execute(
            """
            SELECT
                i.*,
                c.company_name,
                c.sector,
                c.industry,
                q.data_mode,
                q.timestamp_utc AS quote_timestamp_utc,
                l.liquidity_score,
                l.liquidity_class,
                d.quality_score,
                d.quality_class,
                d.staleness_state
            FROM instruments i
            JOIN companies c ON c.company_id = i.company_id
            LEFT JOIN market_quotes q ON q.instrument_id = i.instrument_id
            LEFT JOIN liquidity_snapshots l ON l.instrument_id = i.instrument_id
            LEFT JOIN data_quality_snapshots d ON d.instrument_id = i.instrument_id
            WHERE i.instrument_id = ?
            """,
            (instrument_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_mappings(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM broker_instrument_mappings ORDER BY broker, instrument_id").fetchall()
        return [dict(row) for row in rows]

    def list_conflicts(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM instrument_conflicts ORDER BY created_at DESC").fetchall()
        data: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["brokers_involved"] = json.loads(item["brokers_involved"] or "[]")
            item["payload_json"] = json.loads(item["payload_json"] or "{}")
            data.append(item)
        return data

    def list_quotes(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM market_quotes ORDER BY instrument_id").fetchall()
        return [dict(row) for row in rows]

    def list_quality(self, *, quality_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = ""
        if quality_class:
            where = "WHERE d.quality_class = ?"
            params.append(quality_class)
        rows = self._conn.execute(
            f"""
            SELECT d.*, i.symbol, i.exchange, i.segment, i.instrument_type
            FROM data_quality_snapshots d
            JOIN instruments i ON i.instrument_id = d.instrument_id
            {where}
            ORDER BY d.quality_score DESC, i.symbol
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            item["reasons_json"] = json.loads(item["reasons_json"] or "[]")
            data.append(item)
        return data

    def list_liquidity(self, *, liquidity_class: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        params: List[Any] = []
        where = ""
        if liquidity_class:
            where = "WHERE l.liquidity_class = ?"
            params.append(liquidity_class)
        rows = self._conn.execute(
            f"""
            SELECT l.*, i.symbol, i.exchange, i.segment, i.instrument_type
            FROM liquidity_snapshots l
            JOIN instruments i ON i.instrument_id = l.instrument_id
            {where}
            ORDER BY l.liquidity_score DESC, i.symbol
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            item["reasons_json"] = json.loads(item["reasons_json"] or "[]")
            data.append(item)
        return data

    def list_staleness(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT d.instrument_id, d.staleness_state, d.quote_age_seconds, d.import_age_hours, d.mapping_age_hours, i.symbol, i.exchange, i.segment
            FROM data_quality_snapshots d
            JOIN instruments i ON i.instrument_id = d.instrument_id
            ORDER BY d.quote_age_seconds DESC, i.symbol
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_candidates(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM scanner_candidates ORDER BY eligible DESC, score DESC, symbol").fetchall()
        data = []
        for row in rows:
            item = dict(row)
            item["rejection_reasons_json"] = json.loads(item["rejection_reasons_json"] or "[]")
            item["selection_reasons_json"] = json.loads(item["selection_reasons_json"] or "[]")
            data.append(item)
        return data
