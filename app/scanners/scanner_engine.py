from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.event_bus import EventBus
from app.instruments.repository import InstrumentRepository
from app.market_data.repository import MarketDataRepository
from app.scanners.adx_engine import compute_adx
from app.scanners.atr_engine import compute_atr
from app.scanners.breakout import evaluate_breakout
from app.scanners.candidate import CandidateRecord
from app.scanners.confidence import compute_confidence
from app.scanners.corporate_event_filter import evaluate_corporate_events
from app.scanners.delivery_engine import evaluate_delivery
from app.scanners.ema_engine import compute_emas
from app.scanners.explainability import build_reasoning_lines
from app.scanners.filters import candidate_buckets
from app.scanners.gap_engine import compute_gap
from app.scanners.market_regime import detect_market_regime
from app.scanners.momentum import evaluate_momentum
from app.scanners.news_sentiment import evaluate_news_sentiment
from app.scanners.option_candidate_engine import option_categories
from app.scanners.pullback import evaluate_pullback
from app.scanners.ranking import build_summary, clamp_score, rank_bucket, weighted_score
from app.scanners.relative_strength import evaluate_relative_strength
from app.scanners.risk_filter import evaluate_risk
from app.scanners.rsi_engine import compute_rsi
from app.scanners.sector_rotation import build_sector_rotation
from app.scanners.volume_engine import evaluate_volume
from app.scanners.vwap_engine import evaluate_vwap
from app.settings import Settings
from app.state_store import StateStore


class ScannerEngine:
    def __init__(
        self,
        *,
        settings: Settings,
        state_store: StateStore,
        instrument_repository: InstrumentRepository,
        market_data_repository: MarketDataRepository,
        event_bus: EventBus,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.instrument_repository = instrument_repository
        self.market_data_repository = market_data_repository
        self.event_bus = event_bus

    def refresh(self, *, reason: str = "manual") -> Dict[str, Any]:
        started_at = datetime.now(timezone.utc).isoformat()
        instruments = self.instrument_repository.list_instruments(limit=2000, offset=0)
        quotes = {item["instrument_id"]: item for item in self.instrument_repository.list_quotes()}
        quality = {item["instrument_id"]: item for item in self.instrument_repository.list_quality(limit=2000)}
        liquidity = {item["instrument_id"]: item for item in self.instrument_repository.list_liquidity(limit=2000)}
        corporate_framework = self.state_store.get("scanner_corporate_events") or {}
        news_framework = self.state_store.get("scanner_news_sentiment") or {}

        base_rows: List[Dict[str, Any]] = []
        market_rows: List[Dict[str, Any]] = []
        for instrument in instruments:
            quote = quotes.get(instrument["instrument_id"])
            quality_row = quality.get(instrument["instrument_id"])
            liquidity_row = liquidity.get(instrument["instrument_id"])
            if quote is None or quality_row is None or liquidity_row is None:
                continue
            base_rows.append(
                self._build_base_row(
                    instrument=instrument,
                    quote=quote,
                    quality=quality_row,
                    liquidity=liquidity_row,
                    corporate_events=corporate_framework.get(instrument["symbol"]) or corporate_framework.get(instrument["trading_symbol"]) or [],
                    news_sentiment=news_framework.get(instrument["symbol"]) or news_framework.get(instrument["trading_symbol"]),
                )
            )
            if instrument["segment"] == "CASH":
                market_rows.append(base_rows[-1])

        sector_rotation = build_sector_rotation(base_rows)
        sector_score_map = {item["sector"]: float(item["score"]) for item in sector_rotation}
        market_change_pct = (
            sum(float(item.get("change_pct", 0.0)) for item in market_rows) / len(market_rows) if market_rows else 0.0
        )
        sector_change_map = {
            item["sector"]: float(item["avg_change_pct"])
            for item in sector_rotation
        }
        enriched_profiles = [self._enrich_row(row, sector_score_map, sector_change_map, market_change_pct) for row in base_rows]
        regime = detect_market_regime(enriched_profiles, sum(1 for row in enriched_profiles if row["corporate_risk"] in {"MEDIUM", "HIGH"}))
        candidates = self._materialize_candidates(enriched_profiles)
        self.instrument_repository.replace_candidates(candidates)

        buckets = {
            "intraday": rank_bucket(candidates, "intraday"),
            "btst": rank_bucket(candidates, "btst"),
            "swing": rank_bucket(candidates, "swing"),
            "portfolio": rank_bucket(candidates, "portfolio"),
            "options": rank_bucket(candidates, "options"),
            "watchlist": rank_bucket(candidates, "watchlist"),
            "avoid": rank_bucket(candidates, "avoid"),
            "high_risk": rank_bucket(candidates, "high_risk"),
            "short": rank_bucket(candidates, "short"),
            "corporate_watchlist": rank_bucket(candidates, "corporate_watchlist"),
        }
        summary = build_summary(buckets, regime)
        gainers = sorted(enriched_profiles, key=lambda item: float(item["change_pct"]), reverse=True)[:10]
        losers = sorted(enriched_profiles, key=lambda item: float(item["change_pct"]))[:10]
        risk_heatmap = self._build_risk_heatmap(enriched_profiles)

        state = {
            "last_run": started_at,
            "reason": reason,
            "summary": summary,
            "regime": regime,
            "intraday": buckets["intraday"],
            "btst": buckets["btst"],
            "swing": buckets["swing"],
            "portfolio": buckets["portfolio"],
            "options": buckets["options"],
            "watchlist": buckets["watchlist"],
            "avoid": buckets["avoid"],
            "high_risk": buckets["high_risk"],
            "short": buckets["short"],
            "corporate_events": buckets["corporate_watchlist"],
            "sector_rotation": sector_rotation[:10],
            "risk_heatmap": risk_heatmap[:10],
            "top_gainers": gainers,
            "top_losers": losers,
            "all_candidates": candidates,
        }
        self._emit_transitions(self.state_store.get("scanner_state") or {}, state)
        self.state_store.set("scanner_state", state)
        self.state_store.set("scanner_summary", summary)
        self.instrument_repository.repository.save_state("scanner_summary", summary)
        self.instrument_repository.repository.save_state("scanner_regime", regime)
        self.instrument_repository.save_scanner_run(
            run_id=f"scan-{uuid.uuid4()}",
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            market_regime=str(regime["regime"]),
            summary=summary,
        )
        return state

    def summary(self) -> Dict[str, Any]:
        return (self.state_store.get("scanner_state") or {}).get("summary") or {}

    def bucket(self, name: str) -> List[Dict[str, Any]]:
        return list((self.state_store.get("scanner_state") or {}).get(name) or [])

    def regime(self) -> Dict[str, Any]:
        return dict((self.state_store.get("scanner_state") or {}).get("regime") or {})

    def _build_base_row(
        self,
        *,
        instrument: Dict[str, Any],
        quote: Dict[str, Any],
        quality: Dict[str, Any],
        liquidity: Dict[str, Any],
        corporate_events: List[Dict[str, Any]],
        news_sentiment: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        price = float(quote.get("ltp") or 0.0)
        previous_close = float(quote.get("previous_close") or price or 1.0)
        vwap = float(quote.get("vwap") or price)
        atr = compute_atr(quote)
        atr_pct = round((atr / previous_close) * 100.0, 2) if previous_close > 0 else 0.0
        gap = compute_gap(quote)
        emas = compute_emas(price, vwap, previous_close)
        rsi = compute_rsi(price, previous_close, vwap)
        adx = compute_adx(price, vwap, atr or 0.01)
        vwap_info = evaluate_vwap(price, vwap)
        volume_info = evaluate_volume(quote, float(liquidity["liquidity_score"]))
        delivery_info = evaluate_delivery(instrument, quote)
        corporate_info = evaluate_corporate_events(instrument["symbol"], corporate_events)
        news_info = evaluate_news_sentiment(instrument["symbol"], news_sentiment)
        breakout_score = evaluate_breakout(price, float(quote.get("high") or price), previous_close, vwap)
        pullback_score = evaluate_pullback(price, emas["ema20"], emas["ema50"], float(quote.get("high") or price))
        change_pct = round(((price - previous_close) / previous_close) * 100.0, 2) if previous_close > 0 else 0.0
        spread_pct = round(float(quality.get("spread_pct") or 0.0), 2)
        trend_score = clamp_score(weighted_score({"price": (50.0 + change_pct * 8.0, 1.0), "rsi": (rsi, 0.8), "adx": (adx, 0.7)}))
        trend = "BULLISH" if price >= emas["ema20"] >= emas["ema50"] else "BEARISH" if price <= emas["ema20"] <= emas["ema50"] else "RANGE"
        direction = "SHORT" if trend == "BEARISH" and change_pct < 0 else "LONG"
        return {
            **instrument,
            "quote": quote,
            "quality_row": quality,
            "liquidity_row": liquidity,
            "price": round(price, 2),
            "previous_close": previous_close,
            "change_pct": change_pct,
            "atr": atr,
            "atr_pct": atr_pct,
            "gap_pct": gap["gap_pct"],
            "gap_label": gap["label"],
            "volume_score": volume_info["score"],
            "volume_label": volume_info["label"],
            "vwap_bias": vwap_info["bias"],
            "vwap_score": vwap_info["score"],
            "institutional_score": delivery_info["score"],
            "institutional_label": delivery_info["label"],
            "breakout_score": breakout_score,
            "pullback_score": pullback_score,
            "rsi": round(rsi, 2),
            "adx": round(adx, 2),
            "trend_score": trend_score,
            "trend": trend,
            "direction": direction,
            "ema20": emas["ema20"],
            "ema50": emas["ema50"],
            "ema200": emas["ema200"],
            "spread_pct": spread_pct,
            "liquidity_score_raw": float(liquidity["liquidity_score"]),
            "liquidity_class": liquidity["liquidity_class"],
            "quality_class": quality["quality_class"],
            "staleness_state": quality["staleness_state"],
            "corporate_event_score": float(corporate_info["score"]),
            "corporate_risk": corporate_info["risk"],
            "corporate_events": corporate_info["events"],
            "corporate_reason": corporate_info["reason"],
            "news_score": float(news_info["score"]),
            "news_label": news_info["label"],
            "news_reason": news_info["reason"],
        }

    def _enrich_row(
        self,
        row: Dict[str, Any],
        sector_score_map: Dict[str, float],
        sector_change_map: Dict[str, float],
        market_change_pct: float,
    ) -> Dict[str, Any]:
        sector_score = sector_score_map.get(str(row.get("sector") or "UNKNOWN"), 52.0)
        sector_change_pct = sector_change_map.get(str(row.get("sector") or "UNKNOWN"), 0.0)
        relative_strength_score = evaluate_relative_strength(float(row["change_pct"]), sector_change_pct, market_change_pct)
        momentum_score = evaluate_momentum(float(row["change_pct"]), float(row["rsi"]), float(row["adx"]), float(row["vwap_score"]))
        risk = evaluate_risk(
            spread_pct=float(row["spread_pct"]),
            liquidity_class=str(row["liquidity_class"]),
            quality_class=str(row["quality_class"]),
            staleness_state=str(row["staleness_state"]),
            corporate_risk=str(row["corporate_risk"]),
            news_label=str(row["news_label"]),
        )
        finals = compute_confidence(
            {
                "trend_score": float(row["trend_score"]),
                "momentum_score": momentum_score,
                "volume_score": float(row["volume_score"]),
                "liquidity_score": float(row["liquidity_score_raw"]),
                "institutional_score": float(row["institutional_score"]),
                "sector_score": sector_score,
                "relative_strength_score": relative_strength_score,
                "breakout_score": float(row["breakout_score"]),
                "pullback_score": float(row["pullback_score"]),
                "risk_score": float(risk["score"]),
                "corporate_event_score": float(row["corporate_event_score"]),
                "news_score": float(row["news_score"]),
            }
        )
        eligible = (
            str(row["quality_class"]) not in {"FAILED"}
            and str(row["staleness_state"]) not in {"STALE", "EXPIRED"}
            and str(row["liquidity_class"]) not in {"ILLIQUID"}
        )
        decision = self._decision(
            final_score=float(finals["final_score"]),
            confidence=float(finals["ai_confidence"]),
            risk_level=str(risk["level"]),
            corporate_risk=str(row["corporate_risk"]),
            news_label=str(row["news_label"]),
            eligible=eligible,
        )
        entry = round(float(row["price"]), 2)
        sl = round(max(entry - max(float(row["atr"]), entry * 0.012), 0.01), 2) if row["direction"] == "LONG" else round(entry + max(float(row["atr"]), entry * 0.012), 2)
        t1 = round(entry + (float(row["atr"]) * 1.2), 2) if row["direction"] == "LONG" else round(entry - (float(row["atr"]) * 1.2), 2)
        t2 = round(entry + (float(row["atr"]) * 2.1), 2) if row["direction"] == "LONG" else round(entry - (float(row["atr"]) * 2.1), 2)
        t3 = round(entry + (float(row["atr"]) * 3.3), 2) if row["direction"] == "LONG" else round(entry - (float(row["atr"]) * 3.3), 2)
        stretch = round(entry + (float(row["atr"]) * 4.8), 2) if row["direction"] == "LONG" else round(entry - (float(row["atr"]) * 4.8), 2)
        risk_reward = round(abs((t2 - entry) / max(abs(entry - sl), 0.01)), 2)
        capital_required = round(entry * max(int(row.get("lot_size") or 1), 1), 2)
        extra_reasons = list(risk["reasons"])
        if float(finals["ai_confidence"]) >= 80.0:
            extra_reasons.append("High-confidence composite score.")
        if str(row["direction"]) == "SHORT":
            extra_reasons.append("Relative weakness supports a short-side watch.")
        row.update(
            {
                "sector_score": sector_score,
                "sector_proxy_score": sector_score,
                "relative_strength_score": relative_strength_score,
                "momentum_score": momentum_score,
                "risk_score": float(risk["score"]),
                "risk_level": risk["level"],
                "ai_confidence": float(finals["ai_confidence"]),
                "final_score": float(finals["final_score"]),
                "decision": decision,
                "eligible": eligible,
                "entry": entry,
                "sl": sl,
                "t1": t1,
                "t2": t2,
                "t3": t3,
                "stretch_target": stretch,
                "risk_reward": risk_reward,
                "capital_required": capital_required,
                "expected_hold_time": self._expected_hold_time(str(row["instrument_type"]), decision),
                "intraday_eligible": bool(row["liquidity_row"]["eligible_for_intraday"]),
                "btst_eligible": bool(row["liquidity_row"]["eligible_for_btst"]),
                "swing_eligible": bool(row["liquidity_row"]["eligible_for_swing"]),
                "reason_lines": build_reasoning_lines(
                    {
                        "trend": row["trend"],
                        "rsi": row["rsi"],
                        "adx": row["adx"],
                        "liquidity_class": row["liquidity_class"],
                        "spread_pct": row["spread_pct"],
                        "gap_pct": row["gap_pct"],
                        "vwap_bias": row["vwap_bias"],
                        "corporate_risk": row["corporate_risk"],
                        "news_label": row["news_label"],
                    },
                    extra_reasons,
                ),
            }
        )
        return row

    def _materialize_candidates(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        rows: List[Dict[str, Any]] = []
        for profile in profiles:
            buckets = candidate_buckets(profile) + option_categories(profile)
            unique_buckets = list(dict.fromkeys(buckets))
            if not unique_buckets:
                unique_buckets = ["avoid"]
            for bucket in unique_buckets:
                strategy_scope = self._scope_for_bucket(bucket, profile)
                payload = {
                    "sector": profile.get("sector"),
                    "industry": profile.get("industry"),
                    "price": profile["price"],
                    "volume": profile["quote"].get("volume"),
                    "atr": profile["atr"],
                    "vwap": profile["quote"].get("vwap"),
                    "ema20": profile["ema20"],
                    "ema50": profile["ema50"],
                    "ema200": profile["ema200"],
                    "rsi": profile["rsi"],
                    "adx": profile["adx"],
                    "gap_pct": profile["gap_pct"],
                    "trend": profile["trend"],
                    "liquidity_class": profile["liquidity_class"],
                    "spread_pct": profile["spread_pct"],
                    "corporate_events": profile["corporate_events"],
                    "news": {"label": profile["news_label"], "reason": profile["news_reason"]},
                    "scores": {
                        "trend_score": profile["trend_score"],
                        "momentum_score": profile["momentum_score"],
                        "volume_score": profile["volume_score"],
                        "liquidity_score": profile["liquidity_score_raw"],
                        "institutional_score": profile["institutional_score"],
                        "sector_score": profile["sector_score"],
                        "relative_strength_score": profile["relative_strength_score"],
                        "breakout_score": profile["breakout_score"],
                        "pullback_score": profile["pullback_score"],
                        "risk_score": profile["risk_score"],
                        "corporate_event_score": profile["corporate_event_score"],
                        "news_score": profile["news_score"],
                        "ai_confidence": profile["ai_confidence"],
                        "final_score": profile["final_score"],
                    },
                    "entry": profile["entry"],
                    "sl": profile["sl"],
                    "t1": profile["t1"],
                    "t2": profile["t2"],
                    "t3": profile["t3"],
                    "stretch_target": profile["stretch_target"],
                    "risk_reward": profile["risk_reward"],
                    "capital_required": profile["capital_required"],
                    "lot_size": profile["lot_size"],
                    "expected_hold_time": profile["expected_hold_time"],
                    "reason": " ".join(profile["reason_lines"][:2]),
                    "reason_lines": profile["reason_lines"],
                    "corporate_risk": profile["corporate_risk"],
                    "news_label": profile["news_label"],
                    "market_cap_category": profile.get("market_cap_category"),
                }
                row = CandidateRecord(
                    candidate_id=f"{bucket}:{profile['instrument_id']}",
                    company_id=profile["company_id"],
                    instrument_id=profile["instrument_id"],
                    symbol=profile["symbol"],
                    exchange=profile["exchange"],
                    direction=profile["direction"],
                    instrument_type=profile["instrument_type"],
                    strategy_scope=strategy_scope,
                    score=float(profile["final_score"]),
                    confidence=float(profile["ai_confidence"]),
                    liquidity_score=float(profile["liquidity_score_raw"]),
                    data_quality_score=float(profile["quality_row"]["quality_score"]),
                    fno_eligible=bool(profile["fno_eligible"]),
                    preferred_exchange=str(profile.get("preferred_exchange") or profile["exchange"]),
                    data_mode=str(profile["quote"].get("data_mode") or "FIXTURE"),
                    eligible=bool(profile["eligible"]),
                    candidate_bucket=bucket,
                    decision=str(profile["decision"]),
                    risk_level=str(profile["risk_level"]),
                    payload_json=payload,
                    rejection_reasons_json=[] if profile["eligible"] else profile["reason_lines"],
                    selection_reasons_json=profile["reason_lines"],
                    created_at=now,
                    updated_at=now,
                ).to_dict()
                rows.append(row)
        return rows

    def _decision(
        self,
        *,
        final_score: float,
        confidence: float,
        risk_level: str,
        corporate_risk: str,
        news_label: str,
        eligible: bool,
    ) -> str:
        if not eligible:
            return "NO TRADE"
        if corporate_risk == "HIGH" or news_label == "NEGATIVE":
            return "AVOID"
        if risk_level == "EXTREME":
            return "NO TRADE"
        if final_score >= 78.0 and confidence >= 78.0 and risk_level == "LOW":
            return "BUY"
        if final_score >= 68.0 and risk_level in {"LOW", "MEDIUM"}:
            return "WATCH"
        if risk_level == "HIGH":
            return "REDUCE SIZE"
        if final_score >= 55.0:
            return "WAIT"
        return "AVOID"

    def _expected_hold_time(self, instrument_type: str, decision: str) -> str:
        if instrument_type == "OPTION":
            return "30m-2h"
        if decision == "BUY":
            return "15m-1d"
        if decision in {"WATCH", "WAIT"}:
            return "Observation"
        return "Avoid"

    def _scope_for_bucket(self, bucket: str, profile: Dict[str, Any]) -> str:
        return {
            "intraday": "INTRADAY",
            "btst": "BTST",
            "swing": "SWING",
            "portfolio": "PORTFOLIO",
            "options": "OPTIONS",
            "short": "INTRADAY",
            "watchlist": "INTRADAY" if profile.get("intraday_eligible") else "SWING",
            "avoid": "INTRADAY" if profile.get("intraday_eligible") else "SWING",
            "high_risk": "INTRADAY" if profile.get("intraday_eligible") else "SWING",
            "corporate_watchlist": "SWING",
        }.get(bucket, "INTRADAY")

    def _build_risk_heatmap(self, profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sectors: Dict[str, Dict[str, float]] = {}
        for profile in profiles:
            sector = str(profile.get("sector") or "UNKNOWN")
            item = sectors.setdefault(sector, {"count": 0.0, "risk_total": 0.0, "confidence_total": 0.0})
            item["count"] += 1.0
            item["risk_total"] += float(profile["risk_score"])
            item["confidence_total"] += float(profile["ai_confidence"])
        rows: List[Dict[str, Any]] = []
        for sector, item in sectors.items():
            count = max(item["count"], 1.0)
            rows.append(
                {
                    "sector": sector,
                    "risk_score": round(item["risk_total"] / count, 2),
                    "confidence": round(item["confidence_total"] / count, 2),
                    "classification": "COOL" if (item["risk_total"] / count) >= 68.0 else "HOT" if (item["risk_total"] / count) < 42.0 else "ELEVATED",
                }
            )
        rows.sort(key=lambda item: float(item["risk_score"]))
        return rows

    def _emit_transitions(self, previous: Dict[str, Any], current: Dict[str, Any]) -> None:
        previous_regime = str((previous.get("regime") or {}).get("regime") or "")
        current_regime = str((current.get("regime") or {}).get("regime") or "")
        if previous_regime and previous_regime != current_regime:
            self.event_bus.publish(
                {
                    "event_type": "MARKET_EVENT_DETECTED",
                    "source": "scanner-engine",
                    "severity": "INFO",
                    "title": "Market regime changed",
                    "description": f"{previous_regime} -> {current_regime}",
                    "reason": ", ".join(current["regime"].get("reasons", [])),
                }
            )

        previous_intraday = {item["candidate_id"]: item for item in previous.get("intraday", [])}
        current_intraday = {item["candidate_id"]: item for item in current.get("intraday", [])}
        for candidate_id, item in current_intraday.items():
            if candidate_id not in previous_intraday and float(item.get("confidence", 0.0)) >= 82.0:
                self.event_bus.publish(
                    {
                        "event_type": "SIGNAL_GENERATED",
                        "source": "scanner-engine",
                        "severity": "INFO",
                        "title": f"High confidence scanner signal {item['symbol']}",
                        "description": item.get("payload_json", {}).get("reason", "High-confidence scanner candidate added."),
                        "symbol": item["symbol"],
                        "reason": item.get("decision"),
                    }
                )

        previous_watch = {item["candidate_id"] for item in previous.get("watchlist", [])}
        current_watch = {item["candidate_id"] for item in current.get("watchlist", [])}
        for item in current.get("watchlist", []):
            if item["candidate_id"] not in previous_watch:
                self.event_bus.publish(
                    {
                        "event_type": "WATCHLIST_ADDED",
                        "source": "scanner-engine",
                        "severity": "INFO",
                        "title": f"{item['symbol']} added to watchlist",
                        "description": item.get("payload_json", {}).get("reason", "Scanner watchlist updated."),
                        "symbol": item["symbol"],
                    }
                )
        removed_ids = previous_watch - current_watch
        previous_watch_map = {item["candidate_id"]: item for item in previous.get("watchlist", [])}
        for candidate_id in removed_ids:
            item = previous_watch_map[candidate_id]
            self.event_bus.publish(
                {
                    "event_type": "WATCHLIST_REMOVED",
                    "source": "scanner-engine",
                    "severity": "INFO",
                    "title": f"{item['symbol']} removed from watchlist",
                    "description": "Scanner watchlist no longer includes the symbol.",
                    "symbol": item["symbol"],
                }
            )

        previous_high_risk = {item["candidate_id"] for item in previous.get("high_risk", [])}
        for item in current.get("high_risk", []):
            if item["candidate_id"] not in previous_high_risk:
                self.event_bus.publish(
                    {
                        "event_type": "RISK_BLOCKED",
                        "source": "scanner-engine",
                        "severity": "WARNING",
                        "title": f"Risk increased for {item['symbol']}",
                        "description": item.get("payload_json", {}).get("reason", "Candidate moved to high-risk list."),
                        "symbol": item["symbol"],
                        "reason": item.get("risk_level"),
                    }
                )

        previous_top = [item["symbol"] for item in previous.get("intraday", [])[:5]]
        current_top = [item["symbol"] for item in current.get("intraday", [])[:5]]
        if previous_top and previous_top != current_top:
            self.event_bus.publish(
                {
                    "event_type": "SIGNAL_CHANGED",
                    "source": "scanner-engine",
                    "severity": "INFO",
                    "title": "Scanner ranking changed",
                    "description": f"Top intraday rankings updated to {', '.join(current_top[:5])}.",
                    "reason": "Ranking refresh completed.",
                }
            )

        for item in current.get("corporate_events", [])[:5]:
            if item["candidate_id"] not in {entry["candidate_id"] for entry in previous.get("corporate_events", [])}:
                self.event_bus.publish(
                    {
                        "event_type": "CORPORATE_EVENT_DETECTED",
                        "source": "scanner-engine",
                        "severity": "WARNING",
                        "title": f"Corporate event risk {item['symbol']}",
                        "description": item.get("payload_json", {}).get("reason", "Framework corporate event risk attached."),
                        "symbol": item["symbol"],
                    }
                )
