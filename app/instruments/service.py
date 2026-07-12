from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.event_bus import EventBus
from app.instruments.cache import InstrumentCache
from app.instruments.mapper import resolve_mapping_status, summarize_mapping_states
from app.instruments.models import BrokerInstrumentMappingRecord, CompanyRecord, InstrumentConflictRecord, InstrumentRecord, UniverseStatusRecord
from app.instruments.normalization import alias_match, dedupe_key, names_conflict, normalize_company_name, normalize_symbol
from app.instruments.repository import InstrumentRepository
from app.instruments.universe import FIXTURE_SOURCE_VERSION, load_fixture_universe
from app.market_data.liquidity import evaluate_liquidity
from app.market_data.quality import evaluate_quality
from app.market_data.repository import MarketDataRepository
from app.market_data.spread import evaluate_spread
from app.market_data.staleness import evaluate_staleness
from app.scanners.universe_filter import build_candidates
from app.settings import Settings
from app.state_store import StateStore


class InstrumentService:
    def __init__(
        self,
        settings: Settings,
        state_store: StateStore,
        repository: InstrumentRepository,
        market_data_repository: MarketDataRepository,
        cache: InstrumentCache,
        event_bus: EventBus,
        migration_version_getter: Any,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.repository = repository
        self.market_data_repository = market_data_repository
        self.cache = cache
        self.event_bus = event_bus
        self.migration_version_getter = migration_version_getter
        self._ist_zone = ZoneInfo(self.settings.timezone)

    def start(self) -> Optional[Dict[str, Any]]:
        latest = self.repository.latest_import_run()
        if latest and latest.get("validation_status") == "SUCCESS":
            self._refresh_state()
            return latest
        if self.settings.instrument_import_source.upper() == "NOT_CONFIGURED":
            return None
        return self.import_instruments({"source": self.settings.instrument_import_source})

    def import_instruments(self, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = dict(request or {})
        source = str(payload.get("source") or self.settings.instrument_import_source or "FIXTURE").upper()
        path = payload.get("path") or self.settings.instrument_import_path
        self.event_bus.publish({"event_type": "INSTRUMENT_IMPORT_STARTED", "source": "instrument-service", "severity": "INFO", "title": "Instrument import started", "description": f"Import source {source}"})
        try:
            bundle = self._prepare_bundle(source=source, path=path)
            result = self.cache.replace_snapshot(bundle)
            self._refresh_state()
            self.event_bus.publish({"event_type": "INSTRUMENT_IMPORT_COMPLETED", "source": "instrument-service", "severity": "INFO", "title": "Instrument import completed", "description": f"Imported {len(bundle['instruments'])} instruments.", "reason": source})
            for conflict in self.repository.list_conflicts():
                self.event_bus.publish({"event_type": "INSTRUMENT_CONFLICT_DETECTED", "source": "instrument-service", "severity": "WARNING", "title": conflict["conflict_type"], "description": conflict["reason"], "symbol": conflict.get("symbol"), "reason": conflict["reason"]})
            for mapping in self.repository.list_mappings():
                if mapping["mapping_status"] in {"MISSING", "STALE", "CONFLICT"}:
                    self.event_bus.publish(
                        {
                            "event_type": f"INSTRUMENT_MAPPING_{mapping['mapping_status']}",
                            "source": "instrument-service",
                            "severity": "WARNING",
                            "title": f"{mapping['broker']} mapping {mapping['mapping_status'].lower()}",
                            "description": mapping.get("trading_symbol") or mapping.get("broker_symbol") or mapping["instrument_id"],
                            "symbol": mapping.get("trading_symbol"),
                            "reason": mapping.get("conflict_reason") or mapping["mapping_status"],
                        }
                    )
            for quality in self.repository.list_quality(limit=500):
                if quality["quality_class"] in {"FAILED", "SUSPECT"}:
                    self.event_bus.publish({"event_type": "DATA_QUALITY_DEGRADED", "source": "market-data", "severity": "WARNING", "symbol": quality["symbol"], "description": ", ".join(quality["reasons_json"]), "reason": quality["quality_class"]})
                if quality["staleness_state"] in {"STALE", "EXPIRED"}:
                    self.event_bus.publish({"event_type": "QUOTE_STALE", "source": "market-data", "severity": "WARNING", "symbol": quality["symbol"], "description": f"Quote state {quality['staleness_state']}", "reason": quality["staleness_state"]})
                if quality["spread_state"] == "FAIL":
                    self.event_bus.publish({"event_type": "SPREAD_FILTER_REJECTED", "source": "market-data", "severity": "WARNING", "symbol": quality["symbol"], "description": ", ".join(quality["reasons_json"]), "reason": quality["spread_state"]})
            for liquidity in self.repository.list_liquidity(limit=500):
                if not liquidity["eligible_for_intraday"]:
                    self.event_bus.publish({"event_type": "LIQUIDITY_FILTER_REJECTED", "source": "market-data", "severity": "WARNING", "symbol": liquidity["symbol"], "description": ", ".join(liquidity["reasons_json"]), "reason": liquidity["liquidity_class"]})
            self.event_bus.publish({"event_type": "UNIVERSE_READY", "source": "instrument-service", "severity": "INFO", "title": "Universe ready", "description": "Instrument master loaded and scanner candidates prepared."})
            return result
        except Exception as exc:
            self.event_bus.publish({"event_type": "INSTRUMENT_IMPORT_FAILED", "source": "instrument-service", "severity": "ERROR", "title": "Instrument import failed", "description": str(exc), "reason": source})
            raise

    def _prepare_bundle(self, *, source: str, path: Optional[str]) -> Dict[str, Any]:
        if source == "FIXTURE":
            raw = load_fixture_universe()
        else:
            if not path:
                raise ValueError("instrument import path is required for non-fixture imports")
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            raw["source"] = source
            raw.setdefault("source_version", "manual-v1")
            raw.setdefault("checksum", hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode("utf-8")).hexdigest())
        return self._build_import_bundle(raw)

    def _build_import_bundle(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc.astimezone(self._ist_zone)
        listings = raw["listings"]
        mapping_rows = raw["mappings"]
        quote_rows = raw["quotes"]

        companies_by_key: Dict[str, CompanyRecord] = {}
        instrument_rows: List[Dict[str, Any]] = []
        conflicts: List[InstrumentConflictRecord] = []
        symbol_isin_map: Dict[str, str] = {}
        mapping_lookup: Dict[tuple[str, str, str], Dict[str, Any]] = {
            (row["symbol"], row["exchange"], row["broker"].lower()): row for row in mapping_rows
        }
        quote_lookup: Dict[tuple[str, str, str], Dict[str, Any]] = {
            (row["symbol"], row["exchange"], row["segment"]): row for row in quote_rows
        }

        for index, listing in enumerate(listings, start=1):
            company_key = dedupe_key(listing.get("isin"), listing.get("company_name"))
            current_company = companies_by_key.get(company_key)
            if current_company is None:
                current_company = CompanyRecord(
                    company_id=f"cmp-{index:03d}",
                    company_name=listing["company_name"],
                    isin=listing.get("isin"),
                    sector=listing.get("sector"),
                    industry=listing.get("industry"),
                    market_cap_category=listing.get("market_cap_category"),
                    active=bool(listing.get("active", True)),
                    created_at=now_utc.isoformat(),
                    updated_at=now_utc.isoformat(),
                )
                companies_by_key[company_key] = current_company
            elif current_company.isin == listing.get("isin") and names_conflict(current_company.company_name, listing.get("company_name")):
                conflicts.append(
                    InstrumentConflictRecord(
                        conflict_id=f"conflict-{len(conflicts) + 1:03d}",
                        conflict_type="ISIN_NAME_CONFLICT",
                        symbol=listing.get("symbol"),
                        isin=listing.get("isin"),
                        brokers_involved=[],
                        reason=f"ISIN {listing.get('isin')} maps to both {current_company.company_name} and {listing.get('company_name')}.",
                        resolution_status="OPEN",
                        payload_json={"existing": current_company.to_dict(), "incoming": dict(listing)},
                        created_at=now_utc.isoformat(),
                        updated_at=now_utc.isoformat(),
                    )
                )

            normalized_symbol = normalize_symbol(listing.get("symbol"))
            existing_isin = symbol_isin_map.get(normalized_symbol)
            incoming_isin = (listing.get("isin") or "").upper()
            if existing_isin and incoming_isin and existing_isin != incoming_isin:
                conflicts.append(
                    InstrumentConflictRecord(
                        conflict_id=f"conflict-{len(conflicts) + 1:03d}",
                        conflict_type="SYMBOL_ISIN_CONFLICT",
                        symbol=listing.get("symbol"),
                        isin=incoming_isin,
                        brokers_involved=[],
                        reason=f"Symbol {listing.get('symbol')} maps to multiple ISINs: {existing_isin} and {incoming_isin}.",
                        resolution_status="OPEN",
                        payload_json={"symbol": listing.get("symbol"), "existing_isin": existing_isin, "incoming_isin": incoming_isin},
                        created_at=now_utc.isoformat(),
                        updated_at=now_utc.isoformat(),
                    )
                )
            elif incoming_isin:
                symbol_isin_map[normalized_symbol] = incoming_isin

            instrument_id = self._instrument_id_from_listing(listing)
            fyers_mapping = mapping_lookup.get((listing["symbol"], listing["exchange"], "fyers"), {})
            dhan_mapping = mapping_lookup.get((listing["symbol"], listing["exchange"], "dhan"), {})

            instrument_rows.append(
                InstrumentRecord(
                    instrument_id=instrument_id,
                    company_id=current_company.company_id,
                    exchange=listing["exchange"],
                    segment=listing["segment"],
                    symbol=listing["symbol"],
                    trading_symbol=listing["trading_symbol"],
                    exchange_token=fyers_mapping.get("exchange_token"),
                    broker="fyers",
                    broker_symbol=fyers_mapping.get("broker_symbol"),
                    broker_security_id=dhan_mapping.get("broker_security_id"),
                    isin=listing.get("isin"),
                    instrument_type=listing["instrument_type"],
                    underlying_symbol=listing.get("underlying_symbol"),
                    expiry=listing.get("expiry"),
                    strike=listing.get("strike"),
                    option_type=listing.get("option_type"),
                    lot_size=int(listing.get("lot_size") or 1),
                    tick_size=float(listing.get("tick_size") or 0.05),
                    price_precision=int(listing.get("price_precision") or 2),
                    fno_eligible=bool(listing.get("fno_eligible")),
                    cash_eligible=bool(listing.get("cash_eligible")),
                    bse_code=listing.get("bse_code"),
                    nse_symbol=listing.get("nse_symbol"),
                    currency=listing.get("currency") or "INR",
                    active=bool(listing.get("active", True)),
                    listing_date=listing.get("listing_date"),
                    delisting_date=listing.get("delisting_date"),
                    last_updated=now_utc.isoformat(),
                ).to_dict()
            )

        mapping_records = self._build_mapping_rows(instrument_rows, mapping_rows, conflicts, now_utc)
        preferred_exchange = self._compute_preferred_exchange(companies_by_key, instrument_rows, quote_lookup, mapping_records, now_utc)
        for company in companies_by_key.values():
            preference = preferred_exchange.get(company.company_id, {})
            company.preferred_exchange = preference.get("preferred_exchange")
            company.selection_score = preference.get("selection_score", 0.0)
            company.selection_reason = preference.get("selection_reason", "")

        quotes = self._build_quote_rows(instrument_rows, quote_lookup, now_utc)
        quality_rows, liquidity_rows = self._build_quality_and_liquidity(instrument_rows, mapping_records, quotes, conflicts, now_utc)
        candidates = build_candidates(instrument_rows, quality_rows, liquidity_rows, preferred_exchange, now_utc.isoformat())

        return {
            "source": raw["source"],
            "source_version": raw["source_version"],
            "checksum": raw["checksum"],
            "companies": [company.to_dict() for company in companies_by_key.values()],
            "instruments": instrument_rows,
            "mappings": mapping_records,
            "conflicts": [conflict.to_dict() for conflict in conflicts],
            "quotes": quotes,
            "quality": quality_rows,
            "liquidity": liquidity_rows,
            "candidates": candidates,
        }

    def _instrument_id_from_listing(self, listing: Dict[str, Any]) -> str:
        parts = [listing["exchange"], listing["segment"], listing["trading_symbol"]]
        if listing.get("expiry"):
            parts.append(str(listing["expiry"]))
        if listing.get("strike") is not None:
            parts.append(str(listing["strike"]))
        if listing.get("option_type"):
            parts.append(str(listing["option_type"]))
        return ":".join(parts)

    def _build_mapping_rows(
        self,
        instruments: List[Dict[str, Any]],
        mapping_rows: List[Dict[str, Any]],
        conflicts: List[InstrumentConflictRecord],
        now_utc: datetime,
    ) -> List[Dict[str, Any]]:
        conflict_instruments = {conflict.symbol for conflict in conflicts if conflict.symbol}
        rows: List[Dict[str, Any]] = []
        mapping_lookup = {(row["symbol"], row["exchange"], row["broker"].lower()): row for row in mapping_rows}
        for instrument in instruments:
            for broker in ["fyers", "dhan"]:
                raw_mapping = mapping_lookup.get((instrument["symbol"], instrument["exchange"], broker), {})
                conflict = instrument["symbol"] in conflict_instruments
                status = resolve_mapping_status(
                    broker=broker,
                    broker_symbol=raw_mapping.get("broker_symbol"),
                    broker_security_id=raw_mapping.get("broker_security_id"),
                    exchange_token=raw_mapping.get("exchange_token"),
                    last_verified_timestamp=raw_mapping.get("last_verified_timestamp"),
                    not_configured=False,
                    conflict=conflict,
                    max_age_hours=self.settings.broker_mapping_max_age_hours,
                )
                rows.append(
                    BrokerInstrumentMappingRecord(
                        mapping_id=f"{instrument['instrument_id']}:{broker}",
                        instrument_id=instrument["instrument_id"],
                        company_id=instrument["company_id"],
                        exchange=instrument["exchange"],
                        segment=instrument["segment"],
                        broker=broker,
                        broker_symbol=raw_mapping.get("broker_symbol"),
                        broker_security_id=raw_mapping.get("broker_security_id"),
                        exchange_token=raw_mapping.get("exchange_token"),
                        trading_symbol=instrument["trading_symbol"],
                        instrument_type=instrument["instrument_type"],
                        expiry=instrument.get("expiry"),
                        strike=instrument.get("strike"),
                        option_type=instrument.get("option_type"),
                        lot_size=instrument.get("lot_size"),
                        mapping_status=status,
                        last_verified_timestamp=raw_mapping.get("last_verified_timestamp"),
                        active=bool(instrument.get("active", True)),
                        conflict_reason="Broker mapping conflict." if conflict else None,
                    ).to_dict()
                )
        return rows

    def _compute_preferred_exchange(
        self,
        companies_by_key: Dict[str, CompanyRecord],
        instruments: List[Dict[str, Any]],
        quote_lookup: Dict[tuple[str, str, str], Dict[str, Any]],
        mapping_rows: List[Dict[str, Any]],
        now_utc: datetime,
    ) -> Dict[str, Dict[str, Any]]:
        mapping_by_instrument = {}
        for mapping in mapping_rows:
            mapping_by_instrument.setdefault(mapping["instrument_id"], []).append(mapping)
        company_choices: Dict[str, Dict[str, Any]] = {}
        for instrument in instruments:
            if instrument["segment"] != "CASH" or not instrument["active"]:
                continue
            quote = quote_lookup.get((instrument["symbol"], instrument["exchange"], instrument["segment"]), {})
            mappings = mapping_by_instrument.get(instrument["instrument_id"], [])
            spread = evaluate_spread(quote, self.settings.max_allowed_spread_pct, "FRESH")
            freshness_bonus = 20 if quote.get("timestamp_utc") else 0
            broker_support_bonus = sum(5 for mapping in mappings if mapping["mapping_status"] in {"READY", "PARTIAL"})
            score = (
                min(float(quote.get("traded_value") or 0.0) / 1_000_000.0, 50.0)
                + min(float(quote.get("volume") or 0) / 10_000.0, 20.0)
                + freshness_bonus
                + broker_support_bonus
                + (10 if spread["state"] == "PASS" else 0)
                - (10 if not instrument["active"] else 0)
            )
            reason = f"traded_value={quote.get('traded_value', 0)}, volume={quote.get('volume', 0)}, spread_state={spread['state']}"
            current = company_choices.get(instrument["company_id"])
            preferred = instrument["exchange"]
            if current is None or score > current["selection_score"] or (score == current["selection_score"] and preferred == "NSE"):
                company_choices[instrument["company_id"]] = {
                    "preferred_exchange": preferred,
                    "selection_score": round(score, 2),
                    "selection_reason": reason,
                }
        return company_choices

    def _build_quote_rows(self, instruments: List[Dict[str, Any]], quote_lookup: Dict[tuple[str, str, str], Dict[str, Any]], now_utc: datetime) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for instrument in instruments:
            raw_quote = dict(quote_lookup[(instrument["symbol"], instrument["exchange"], instrument["segment"])])
            timestamp_utc = raw_quote["timestamp_utc"]
            timestamp_ist = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00")).astimezone(self._ist_zone).isoformat()
            rows.append(
                {
                    "instrument_id": instrument["instrument_id"],
                    "source": raw_quote["source"],
                    "timestamp_utc": timestamp_utc,
                    "timestamp_ist": timestamp_ist,
                    "ltp": raw_quote.get("ltp"),
                    "open": raw_quote.get("open"),
                    "high": raw_quote.get("high"),
                    "low": raw_quote.get("low"),
                    "previous_close": raw_quote.get("previous_close"),
                    "bid": raw_quote.get("bid"),
                    "ask": raw_quote.get("ask"),
                    "bid_quantity": raw_quote.get("bid_quantity"),
                    "ask_quantity": raw_quote.get("ask_quantity"),
                    "volume": raw_quote.get("volume"),
                    "traded_value": raw_quote.get("traded_value"),
                    "vwap": raw_quote.get("vwap"),
                    "open_interest": raw_quote.get("open_interest"),
                    "change_in_oi": raw_quote.get("change_in_oi"),
                    "data_mode": raw_quote.get("data_mode"),
                    "sequence_number": raw_quote.get("sequence_number"),
                    "received_at": raw_quote.get("received_at"),
                }
            )
        return rows

    def _build_quality_and_liquidity(
        self,
        instruments: List[Dict[str, Any]],
        mapping_rows: List[Dict[str, Any]],
        quotes: List[Dict[str, Any]],
        conflicts: List[InstrumentConflictRecord],
        now_utc: datetime,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        quote_by_instrument = {quote["instrument_id"]: quote for quote in quotes}
        mappings_by_instrument: Dict[str, List[Dict[str, Any]]] = {}
        for mapping in mapping_rows:
            mappings_by_instrument.setdefault(mapping["instrument_id"], []).append(mapping)
        conflict_symbols = {conflict.symbol for conflict in conflicts if conflict.symbol}
        quality_rows: List[Dict[str, Any]] = []
        liquidity_rows: List[Dict[str, Any]] = []
        for instrument in instruments:
            quote = quote_by_instrument[instrument["instrument_id"]]
            mapping_set = mappings_by_instrument.get(instrument["instrument_id"], [])
            max_mapping_age = 0.0
            for mapping in mapping_set:
                if mapping.get("last_verified_timestamp"):
                    verified = datetime.fromisoformat(mapping["last_verified_timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc)
                    max_mapping_age = max(max_mapping_age, (now_utc - verified).total_seconds() / 3600)
            staleness = evaluate_staleness(
                timestamp_utc=quote["timestamp_utc"],
                import_timestamp=self.repository.latest_import_run()["import_timestamp"] if self.repository.latest_import_run() else now_utc.isoformat(),
                mapping_age_hours=max_mapping_age,
                now_utc=now_utc,
                quote_fresh_seconds=self.settings.quote_fresh_seconds,
                quote_aging_seconds=self.settings.quote_aging_seconds,
                instrument_master_max_age_hours=self.settings.instrument_master_max_age_hours,
                broker_mapping_max_age_hours=self.settings.broker_mapping_max_age_hours,
                data_mode=quote["data_mode"],
            )
            spread = evaluate_spread(quote, self.settings.max_allowed_spread_pct, staleness["state"])
            liquidity = evaluate_liquidity(
                quote,
                staleness["state"],
                min_intraday_traded_value=self.settings.min_intraday_traded_value,
                min_btst_traded_value=self.settings.min_btst_traded_value,
                min_swing_traded_value=self.settings.min_swing_traded_value,
                min_option_oi=self.settings.min_option_oi,
                min_option_volume=self.settings.min_option_volume,
                max_allowed_spread_pct=self.settings.max_allowed_spread_pct,
                instrument_type=instrument["instrument_type"],
                fno_eligible=bool(instrument["fno_eligible"]),
            )
            quality = evaluate_quality(
                instrument=instrument,
                quote=quote,
                mapping_rows=mapping_set,
                spread=spread,
                staleness=staleness,
                has_conflict=instrument["symbol"] in conflict_symbols,
                now_utc=now_utc,
            )
            quality_rows.append(
                {
                    "instrument_id": instrument["instrument_id"],
                    "quality_score": quality["quality_score"],
                    "quality_class": quality["quality_class"],
                    "reasons_json": quality["reasons"],
                    "staleness_state": staleness["state"],
                    "quote_age_seconds": staleness["quote_age_seconds"],
                    "import_age_hours": staleness["import_age_hours"],
                    "mapping_age_hours": staleness["mapping_age_hours"],
                    "spread_state": spread["state"],
                    "spread_pct": spread["spread_pct"],
                    "completeness_score": quality["completeness_score"],
                    "conflict_state": "CONFLICT" if instrument["symbol"] in conflict_symbols else "CLEAR",
                    "created_at": now_utc.isoformat(),
                }
            )
            liquidity_rows.append(
                {
                    "instrument_id": instrument["instrument_id"],
                    "quote_timestamp_utc": quote["timestamp_utc"],
                    "liquidity_score": liquidity["liquidity_score"],
                    "liquidity_class": liquidity["liquidity_class"],
                    "reasons_json": liquidity["reasons"],
                    "eligible_for_intraday": int(liquidity["eligible_for_intraday"]),
                    "eligible_for_btst": int(liquidity["eligible_for_btst"]),
                    "eligible_for_swing": int(liquidity["eligible_for_swing"]),
                    "eligible_for_options": int(liquidity["eligible_for_options"]),
                    "created_at": now_utc.isoformat(),
                }
            )
        return quality_rows, liquidity_rows

    def _refresh_state(self) -> None:
        status = self.universe_status()
        self.state_store.set("universe_status", status)
        self.state_store.set("universe_conflicts", self.repository.list_conflicts())
        self.state_store.set("market_data_quality", self.repository.list_quality(limit=500))
        self.state_store.set("market_data_liquidity", self.repository.list_liquidity(limit=500))
        self.state_store.set("market_data_staleness", self.repository.list_staleness(limit=500))
        self.state_store.set("scanner_candidates", self.repository.list_candidates())

    def universe_status(self) -> Dict[str, Any]:
        companies = self.repository.list_companies(limit=1000, offset=0)
        instruments = self.repository.list_instruments(limit=2000, offset=0)
        conflicts = self.repository.list_conflicts()
        latest_run = self.repository.latest_import_run()
        mappings = self.repository.list_mappings()
        quality = self.repository.list_quality(limit=2000)
        liquidity = self.repository.list_liquidity(limit=2000)
        staleness = self.repository.list_staleness(limit=2000)
        selection_summary = {"NSE": 0, "BSE": 0}
        for company in companies:
            preferred = self._company_preference(company["company_id"], instruments)
            if preferred in selection_summary:
                selection_summary[preferred] += 1
        status = UniverseStatusRecord(
            total_companies=len(companies),
            total_instruments=len(instruments),
            nse_count=sum(1 for item in instruments if item["exchange"] == "NSE"),
            bse_count=sum(1 for item in instruments if item["exchange"] == "BSE"),
            fno_count=sum(1 for item in instruments if item["fno_eligible"]),
            active_count=sum(1 for item in instruments if item["active"]),
            conflict_count=len(conflicts),
            last_import_time=latest_run["completed_at"] if latest_run else None,
            import_source=latest_run["source"] if latest_run else "NOT_CONFIGURED",
            source_version=latest_run["source_version"] if latest_run else None,
            migration_version=str(self.migration_version_getter() or "000"),
            broker_mapping_summary=summarize_mapping_states(mappings),
            quality_class_counts=self._count_by_key(quality, "quality_class"),
            liquidity_class_counts=self._count_by_key(liquidity, "liquidity_class"),
            stale_state_counts=self._count_by_key(staleness, "staleness_state"),
            ready=bool(latest_run and latest_run["validation_status"] == "SUCCESS"),
            selection_summary=selection_summary,
        )
        return status.to_dict()

    def _company_preference(self, company_id: str, instruments: List[Dict[str, Any]]) -> Optional[str]:
        choices = [item for item in instruments if item["company_id"] == company_id and item["segment"] == "CASH"]
        if not choices:
            return None
        choices.sort(key=lambda item: (item["liquidity_score"] or 0, item["quality_score"] or 0, item["exchange"] == "NSE"), reverse=True)
        return choices[0]["exchange"]

    def _count_by_key(self, rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            name = str(row.get(key) or "UNKNOWN")
            counts[name] = counts.get(name, 0) + 1
        return counts

    def list_instruments(self, **filters: Any) -> List[Dict[str, Any]]:
        instruments = self.repository.list_instruments(**filters)
        for instrument in instruments:
            instrument["preferred_exchange"] = self._company_preference(instrument["company_id"], self.repository.list_instruments(limit=2000, offset=0))
        return instruments

    def get_instrument(self, instrument_id: str) -> Optional[Dict[str, Any]]:
        instrument = self.repository.get_instrument(instrument_id)
        if instrument:
            instrument["preferred_exchange"] = self._company_preference(instrument["company_id"], self.repository.list_instruments(limit=2000, offset=0))
        return instrument

    def list_companies(self, **filters: Any) -> List[Dict[str, Any]]:
        companies = self.repository.list_companies(**filters)
        all_instruments = self.repository.list_instruments(limit=2000, offset=0)
        for company in companies:
            company["preferred_exchange"] = self._company_preference(company["company_id"], all_instruments)
        return companies

    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        company = self.repository.get_company(company_id)
        if company:
            company["preferred_exchange"] = self._company_preference(company_id, self.repository.list_instruments(limit=2000, offset=0))
        return company
