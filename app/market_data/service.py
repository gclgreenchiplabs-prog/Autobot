from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from app.audit.repository import AuditTimelineRepository
from app.brokers.dhan.market_data import DhanMarketDataAdapter
from app.brokers.fyers.market_data import FyersMarketDataAdapter
from app.event_bus import EventBus
from app.instruments.repository import InstrumentRepository
from app.market_data.adapters.fixture import FixtureMarketDataAdapter
from app.market_data.base import AdapterState, DataState, MarketDataAdapter, NormalizedTick
from app.market_data.candle_builder import CandleBuilder
from app.market_data.events import market_data_event
from app.market_data.heartbeat import HeartbeatMonitor
from app.market_data.quote_cache import LatestQuoteCache
from app.market_data.reconnect import ReconnectPolicy
from app.market_data.repository import MarketDataRepository
from app.market_data.sequence import SequenceTracker
from app.market_data.subscriptions import SubscriptionRegistry
from app.market_data.tick_validator import TickValidator
from app.settings import Settings
from app.state_store import StateStore


class MarketDataService:
    def __init__(
        self,
        *,
        settings: Settings,
        state_store: StateStore,
        repository: MarketDataRepository,
        instrument_repository: InstrumentRepository,
        event_bus: EventBus,
        audit_repository: AuditTimelineRepository,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.repository = repository
        self.instrument_repository = instrument_repository
        self.event_bus = event_bus
        self.audit_repository = audit_repository
        self.subscription_registry = SubscriptionRegistry()
        self.quote_cache = LatestQuoteCache()
        self.sequence_tracker = SequenceTracker()
        self.heartbeat = HeartbeatMonitor(settings)
        self.reconnect_policy = ReconnectPolicy(
            initial_seconds=settings.market_data_reconnect_initial_seconds,
            max_seconds=settings.market_data_reconnect_max_seconds,
            max_attempts=settings.market_data_max_reconnect_attempts,
            jitter_fn=lambda attempt: settings.market_data_reconnect_jitter_seconds,
        )
        self.tick_validator = TickValidator(settings, instrument_repository)
        enabled_timeframes = []
        if settings.enable_1m_candles:
            enabled_timeframes.append("1m")
        if settings.enable_5m_candles:
            enabled_timeframes.append("5m")
        if settings.enable_15m_candles:
            enabled_timeframes.append("15m")
        if settings.enable_30m_candles:
            enabled_timeframes.append("30m")
        if settings.enable_daily_candles:
            enabled_timeframes.append("1d")
        self.candle_builder = CandleBuilder(timezone_name=settings.timezone, enabled_timeframes=enabled_timeframes)
        self.adapters: Dict[str, MarketDataAdapter] = {
            "fyers": FyersMarketDataAdapter(settings),
            "dhan": DhanMarketDataAdapter(settings),
            "fixture": FixtureMarketDataAdapter(timezone_name=settings.timezone, auto_start=settings.fixture_auto_start),
        }
        self.active_source = "fixture" if settings.market_data_mode == "FIXTURE" else settings.primary_market_data_broker.lower()
        self.started = False
        self._notification_cooldowns: Dict[str, str] = {}

    def start(self) -> Dict[str, Any]:
        self.started = True
        for source, adapter in self.adapters.items():
            readiness = adapter.readiness()
            self.repository.upsert_connection(
                source=source,
                connection_state=readiness["state"],
                data_state=readiness["data_state"],
                readiness_json=readiness,
            )
        self._refresh_state()
        if self.settings.market_data_mode == "FIXTURE" and self.settings.fixture_auto_start:
            self.start_fixture()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        for adapter in self.adapters.values():
            adapter.disconnect()
        self.started = False
        self._refresh_state()
        return self.status()

    def adapter_readiness(self) -> Dict[str, Dict[str, Any]]:
        return {name: adapter.readiness() for name, adapter in self.adapters.items()}

    def status(self) -> Dict[str, Any]:
        heartbeat = self.heartbeat.snapshot(
            active_subscription_count=self.subscription_registry.active_count(source=self.active_source),
            stale_instrument_count=self.stale_instrument_count(),
            quote_cache_size=self.quote_cache.size(),
        )
        candles = self.repository.list_candles(limit=500)
        data = {
            "enabled": self.settings.enable_market_data,
            "market_data_mode": self.settings.market_data_mode.lower(),
            "active_market_data_source": self.active_source,
            "primary_market_data_broker": self.settings.primary_market_data_broker.lower(),
            "standby_market_data_broker": self.settings.standby_market_data_broker.lower(),
            "primary_connection_state": self.adapters[self.settings.primary_market_data_broker.lower()].readiness()["state"],
            "standby_connection_state": self.adapters[self.settings.standby_market_data_broker.lower()].readiness()["state"],
            "fixture_connection_state": self.adapters["fixture"].readiness()["state"],
            "quote_cache_size": self.quote_cache.size(),
            "latest_quote_count": len(self.repository.list_latest_quotes()),
            "active_subscriptions": self.subscription_registry.active_count(),
            "subscription_count": self.subscription_registry.subscription_count(),
            "stale_instruments": self.stale_instrument_count(),
            "candle_builder_state": "READY" if self.started else "STOPPED",
            "completed_candles": self._count_completed_candles(candles),
            "heartbeat": heartbeat,
            "adapter_readiness": self.adapter_readiness(),
        }
        self.state_store.set("market_data_status", data)
        return data

    def connections(self) -> List[Dict[str, Any]]:
        return self.repository.list_connections()

    def subscriptions(self) -> List[Dict[str, Any]]:
        return self.repository.list_subscriptions()

    def quotes(self, *, instrument_id: Optional[str] = None) -> List[Dict[str, Any]] | Dict[str, Any] | None:
        if instrument_id:
            return self.quote_cache.get(instrument_id)
        return self.quote_cache.snapshot()

    def candles(self, *, instrument_id: Optional[str] = None, timeframe: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        current = self.candle_builder.current_candles()
        completed = self.repository.list_candles(instrument_id=instrument_id, timeframe=timeframe, limit=limit)
        rows = completed + current
        if instrument_id:
            rows = [row for row in rows if row["instrument_id"] == instrument_id]
        if timeframe:
            rows = [row for row in rows if row["timeframe"] == timeframe]
        return rows[:limit]

    def rejections(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        return self.repository.list_tick_rejections(limit=limit)

    def events(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        return self.repository.list_market_data_events(limit=limit)

    def heartbeat_snapshot(self) -> Dict[str, Any]:
        return self.status()["heartbeat"]

    def connect(self, source: Optional[str] = None) -> Dict[str, Any]:
        chosen = self._choose_source(source)
        adapter = self.adapters[chosen]
        result = adapter.connect()
        self.active_source = chosen
        self.repository.upsert_connection(
            source=chosen,
            connection_state=result["connection_state"],
            data_state=result.get("data_state", DataState.NOT_READY.value),
            readiness_json=result,
        )
        event_type = "MARKET_DATA_CONNECTED" if adapter.is_connected() else "MARKET_DATA_FAILED"
        self._emit_market_data_event(
            event_type,
            source=chosen,
            severity="INFO" if adapter.is_connected() else "WARNING",
            title=f"{chosen.upper()} market data {event_type.lower().replace('_', ' ')}",
            description=result.get("reason", result["connection_state"]),
            action_taken="connected" if adapter.is_connected() else "awaiting configuration",
        )
        self.audit_repository.record(
            module="market-data",
            event_type="source_selected",
            source=chosen,
            new_value_json={"active_source": chosen, "readiness": result},
            reason="control connect",
        )
        self._refresh_state()
        return result

    def disconnect(self, source: Optional[str] = None) -> Dict[str, Any]:
        chosen = self._choose_source(source)
        result = self.adapters[chosen].disconnect()
        self.repository.upsert_connection(
            source=chosen,
            connection_state=result["connection_state"],
            data_state=result.get("data_state", DataState.NOT_READY.value),
            readiness_json=result,
        )
        self._emit_market_data_event(
            "MARKET_DATA_DISCONNECTED",
            source=chosen,
            severity="WARNING",
            title=f"{chosen.upper()} market data disconnected",
            description="Market-data adapter disconnected.",
            action_taken="disconnected",
        )
        self._refresh_state()
        return result

    def reconnect(self, source: Optional[str] = None) -> Dict[str, Any]:
        chosen = self._choose_source(source)
        delay = self.reconnect_policy.next_delay()
        self.heartbeat.record_reconnect()
        self._emit_market_data_event(
            "MARKET_DATA_RECONNECTING",
            source=chosen,
            severity="WARNING",
            title=f"{chosen.upper()} market data reconnecting",
            description=f"Reconnect attempt {self.reconnect_policy.state.attempt}.",
            action_taken=f"retry in {delay}s" if delay is not None else "max retries reached",
        )
        self.audit_repository.record(
            module="market-data",
            event_type="reconnect_initiated",
            source=chosen,
            new_value_json=self.reconnect_policy.state.to_dict(),
            reason="manual reconnect",
        )
        result = self.adapters[chosen].reconnect()
        self.sequence_tracker.reset_source(chosen)
        self.subscription_registry.resubscribe_snapshot(chosen)
        self.repository.save_reconnect(source=chosen, attempt=self.reconnect_policy.state.attempt, delay_seconds=delay or 0.0, status=result["connection_state"])
        self.repository.upsert_connection(
            source=chosen,
            connection_state=result["connection_state"],
            data_state=result.get("data_state", DataState.NOT_READY.value),
            readiness_json=result,
        )
        event_type = "MARKET_DATA_RECONNECTED" if self.adapters[chosen].is_connected() else "MARKET_DATA_FAILED"
        self._emit_market_data_event(
            event_type,
            source=chosen,
            severity="INFO" if self.adapters[chosen].is_connected() else "ERROR",
            title=f"{chosen.upper()} market data {event_type.lower().replace('_', ' ')}",
            description=result.get("reason", result["connection_state"]),
            action_taken="resubscribed pending",
        )
        self._refresh_state()
        return result

    def subscribe(
        self,
        *,
        instrument_ids: Iterable[str],
        consumer: str = "api",
        source: Optional[str] = None,
        timeframes: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        chosen = self._choose_source(source)
        instruments = []
        records = []
        for instrument_id in instrument_ids:
            instrument = self.instrument_repository.get_instrument(instrument_id)
            if instrument is None:
                raise ValueError(f"instrument not found: {instrument_id}")
            broker_symbol = self._broker_symbol_for_source(instrument_id, chosen) or instrument["trading_symbol"]
            records.append(
                self.subscription_registry.subscribe(
                    instrument_id=instrument_id,
                    source=chosen,
                    broker_symbol=broker_symbol,
                    consumer=consumer,
                    timeframes=timeframes,
                )
            )
            self.repository.upsert_subscription(records[-1])
            instruments.append(instrument)
            self.audit_repository.record(
                module="market-data",
                event_type="subscription_requested",
                source=chosen,
                instrument_id=instrument_id,
                new_value_json=records[-1],
                reason="consumer subscribe",
            )
        result = self.adapters[chosen].subscribe(instruments)
        for instrument in instruments:
            active = self.subscription_registry.mark_active(chosen, instrument["instrument_id"])
            if active:
                self.repository.upsert_subscription(active)
                self.audit_repository.record(
                    module="market-data",
                    event_type="subscription_activated",
                    source=chosen,
                    instrument_id=instrument["instrument_id"],
                    new_value_json=active,
                    reason="adapter subscribe completed",
                )
        self.repository.upsert_connection(
            source=chosen,
            connection_state=self.adapters[chosen].readiness()["state"],
            data_state=self.adapters[chosen].readiness()["data_state"],
            readiness_json=self.adapters[chosen].readiness(),
        )
        if chosen == "fixture" and self.adapters["fixture"].is_connected():
            self._emit_fixture_ticks()
        self._refresh_state()
        return {"source": chosen, "subscriptions": records, "adapter": result}

    def unsubscribe(self, *, instrument_ids: Iterable[str], consumer: str = "api", source: Optional[str] = None) -> Dict[str, Any]:
        chosen = self._choose_source(source)
        instruments = []
        results = []
        for instrument_id in instrument_ids:
            instrument = self.instrument_repository.get_instrument(instrument_id)
            if instrument is None:
                continue
            instruments.append(instrument)
            record = self.subscription_registry.unsubscribe(instrument_id=instrument_id, source=chosen, consumer=consumer)
            if record is not None:
                self.repository.upsert_subscription(record)
                results.append(record)
        adapter_result = self.adapters[chosen].unsubscribe(instruments)
        self._refresh_state()
        return {"source": chosen, "subscriptions": results, "adapter": adapter_result}

    def start_fixture(self) -> Dict[str, Any]:
        if self.settings.market_data_mode != "FIXTURE":
            raise ValueError("fixture controls require MARKET_DATA_MODE=FIXTURE")
        result = self.connect("fixture")
        self._emit_fixture_ticks()
        self._refresh_state()
        return result

    def stop_fixture(self) -> Dict[str, Any]:
        return self.disconnect("fixture")

    def process_adapter_ticks(self, source: Optional[str] = None, count: int = 1) -> List[Dict[str, Any]]:
        chosen = self._choose_source(source)
        if chosen != "fixture":
            return []
        return self._emit_fixture_ticks(count=count)

    def _emit_fixture_ticks(self, count: int = 1) -> List[Dict[str, Any]]:
        adapter = self.adapters["fixture"]
        raw_ticks = adapter.emit_next_ticks(count=count) if isinstance(adapter, FixtureMarketDataAdapter) else []
        persisted: List[Dict[str, Any]] = []
        for raw_tick in raw_ticks:
            persisted.append(self.ingest_tick(raw_tick))
        return persisted

    def ingest_tick(self, tick_payload: Dict[str, Any]) -> Dict[str, Any]:
        tick = NormalizedTick.create(timezone_name=self.settings.timezone, **tick_payload).to_dict()
        self.heartbeat.record_socket_message(tick["timestamp_received"])
        validation = self.tick_validator.validate(tick)
        sequence = self.sequence_tracker.evaluate(tick, fingerprint=validation["fingerprint"])

        if validation["state"] not in {"VALID", "STALE"}:
            return self._reject_tick(tick, validation["state"], validation["reasons"])
        if sequence["state"] == "DUPLICATE":
            return self._reject_tick(tick, "DUPLICATE", [sequence["reason"]], material=False)
        if sequence["state"] == "OUT_OF_ORDER":
            return self._reject_tick(tick, "OUT_OF_ORDER", [sequence["reason"]])
        if validation["state"] == "STALE":
            return self._reject_tick(tick, "STALE", validation["reasons"])

        self.repository.save_tick(tick)
        self.repository.save_sequence(
            source=tick["source"],
            instrument_id=tick["instrument_id"],
            sequence_number=tick.get("sequence_number"),
            timestamp_utc=tick["timestamp_utc"],
            fingerprint=validation["fingerprint"],
        )
        updated = self.quote_cache.update(tick)
        if updated:
            self.repository.upsert_latest_quote(tick)
        self.repository.upsert_quote_projection(tick)
        self.heartbeat.record_valid_tick(tick["timestamp_utc"])
        subscription = self.subscription_registry.touch_tick(tick["source"], tick["instrument_id"], tick["timestamp_utc"])
        if subscription is not None:
            self.repository.upsert_subscription(subscription)
        self.repository.save_heartbeat(source=tick["source"], payload=self.heartbeat_snapshot())

        completed_candles = self.candle_builder.ingest(tick)
        for candle in completed_candles:
            self.repository.save_candle(candle)
            self._emit_market_data_event(
                "CANDLE_COMPLETED",
                source=tick["source"],
                severity="INFO",
                title=f"Candle completed {candle['timeframe']}",
                description=f"{tick['symbol']} {candle['timeframe']} candle completed.",
                instrument_id=tick["instrument_id"],
                symbol=tick["symbol"],
                action_taken="persisted candle",
            )
        if sequence["state"] == "WARNING":
            self._emit_market_data_event(
                "SEQUENCE_GAP_DETECTED",
                source=tick["source"],
                severity="WARNING",
                title="Sequence gap detected",
                description=sequence["reason"],
                instrument_id=tick["instrument_id"],
                symbol=tick["symbol"],
                reason=sequence["reason"],
                action_taken="persisted for audit",
            )
            self.audit_repository.record(
                module="market-data",
                event_type="sequence_gap",
                source=tick["source"],
                instrument_id=tick["instrument_id"],
                new_value_json={"tick": tick, "sequence": sequence},
                reason=sequence["reason"],
            )
        self._refresh_state()
        return tick

    def stale_instrument_count(self) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for quote in self.quote_cache.snapshot():
            tick_time = datetime.fromisoformat(quote["timestamp_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
            if (now - tick_time).total_seconds() >= self.settings.market_data_stale_seconds:
                count += 1
        return count

    def detect_feed_health(self) -> Dict[str, Any]:
        heartbeat = self.heartbeat_snapshot()
        state = heartbeat["state"]
        if state == "STALE":
            self._emit_market_data_event(
                "MARKET_DATA_STALE",
                source=self.active_source,
                severity="WARNING",
                title="Market data stale",
                description="Heartbeat or quote age crossed the stale threshold.",
                action_taken="marked stale",
            )
        elif state == "FAILED":
            self._emit_market_data_event(
                "MARKET_DATA_FAILED",
                source=self.active_source,
                severity="ERROR",
                title="Market data failed",
                description="Heartbeat crossed the failed threshold.",
                action_taken="service degraded",
            )
        self._refresh_state()
        return heartbeat

    def _reject_tick(self, tick: Dict[str, Any], state: str, reasons: List[str], *, material: bool = True) -> Dict[str, Any]:
        self.repository.save_tick_rejection(tick=tick, rejection_state=state, reasons=reasons)
        self.audit_repository.record(
            module="market-data",
            event_type="tick_rejected",
            source=tick["source"],
            instrument_id=tick["instrument_id"],
            new_value_json={"tick": tick, "state": state, "reasons": reasons},
            reason=", ".join(reasons),
        )
        if material:
            self._emit_market_data_event(
                "TICK_REJECTED",
                source=tick["source"],
                severity="WARNING",
                title="Tick rejected",
                description=", ".join(reasons),
                instrument_id=tick["instrument_id"],
                symbol=tick["symbol"],
                reason=state,
                action_taken="quarantined",
            )
        self._refresh_state()
        return {"state": state, "reasons": reasons, "tick": tick}

    def _emit_market_data_event(
        self,
        event_type: str,
        *,
        source: str,
        severity: str,
        title: str,
        description: str,
        instrument_id: Optional[str] = None,
        symbol: Optional[str] = None,
        reason: Optional[str] = None,
        action_taken: Optional[str] = None,
    ) -> Dict[str, Any]:
        key = f"{event_type}:{source}:{instrument_id or '*'}"
        if self._notification_cooldowns.get(key) == description:
            return {"event_type": event_type, "suppressed": True}
        self._notification_cooldowns[key] = description
        event = market_data_event(
            event_type,
            source=source,
            severity=severity,
            title=title,
            description=description,
            instrument_id=instrument_id,
            symbol=symbol,
            reason=reason,
            action_taken=action_taken,
        )
        self.repository.save_market_data_event(event)
        self.event_bus.publish(event)
        return event

    def _choose_source(self, source: Optional[str]) -> str:
        chosen = (source or self.active_source or "fixture").lower()
        if chosen not in self.adapters:
            raise ValueError(f"unsupported market-data source: {chosen}")
        return chosen

    def _broker_symbol_for_source(self, instrument_id: str, source: str) -> Optional[str]:
        for mapping in self.instrument_repository.list_mappings():
            if mapping["instrument_id"] == instrument_id and mapping["broker"] == source:
                return mapping.get("broker_symbol") or mapping.get("trading_symbol")
        return None

    def _count_completed_candles(self, rows: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            timeframe = row["timeframe"]
            counts[timeframe] = counts.get(timeframe, 0) + 1
        return counts

    def _refresh_state(self) -> None:
        self.state_store.set("market_data_status", self.status())
        self.state_store.set("market_data_connections", self.connections())
        self.state_store.set("market_data_subscriptions", self.subscriptions())
        self.state_store.set("market_data_quotes", self.quote_cache.snapshot())
        self.state_store.set("market_data_candles", self.repository.list_candles(limit=500))
        self.state_store.set("market_data_rejections", self.rejections(limit=500))
        self.state_store.set("market_data_events_live", self.events(limit=500))
