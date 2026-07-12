from __future__ import annotations

from typing import Dict, Iterable, List


def clamp_score(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, float(value))), 2)


def weighted_score(components: Dict[str, tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in components.values()) or 1.0
    value = sum(score * weight for score, weight in components.values()) / total_weight
    return clamp_score(value)


def rank_bucket(candidates: Iterable[Dict[str, object]], bucket: str, limit: int = 20) -> List[Dict[str, object]]:
    rows = [item for item in candidates if item.get("candidate_bucket") == bucket]
    rows.sort(
        key=lambda item: (
            bool(item.get("eligible")),
            float(item.get("score", 0.0)),
            float(item.get("confidence", 0.0)),
            float(item.get("payload_json", {}).get("scores", {}).get("risk_score", 0.0)),
        ),
        reverse=True,
    )
    return rows[:limit]


def build_summary(buckets: Dict[str, List[Dict[str, object]]], regime: Dict[str, object]) -> Dict[str, object]:
    top_intraday = buckets.get("intraday", [])
    top_options = buckets.get("options", [])
    return {
        "market_regime": regime.get("regime", "RANGE"),
        "regime_reasons": regime.get("reasons", []),
        "intraday_count": len(top_intraday),
        "options_count": len(top_options),
        "btst_count": len(buckets.get("btst", [])),
        "swing_count": len(buckets.get("swing", [])),
        "portfolio_count": len(buckets.get("portfolio", [])),
        "watchlist_count": len(buckets.get("watchlist", [])),
        "avoid_count": len(buckets.get("avoid", [])),
        "high_risk_count": len(buckets.get("high_risk", [])),
        "short_count": len(buckets.get("short", [])),
        "corporate_watchlist_count": len(buckets.get("corporate_watchlist", [])),
        "top_intraday_symbol": top_intraday[0]["symbol"] if top_intraday else None,
        "top_options_symbol": top_options[0]["symbol"] if top_options else None,
        "high_confidence_signals": sum(1 for item in top_intraday if float(item.get("confidence", 0.0)) >= 80.0),
    }
