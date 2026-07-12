from __future__ import annotations

from typing import Any, Dict, Iterable, List


def evaluate_quality(
    *,
    instrument: Dict[str, Any],
    quote: Dict[str, Any],
    mapping_rows: Iterable[Dict[str, Any]],
    spread: Dict[str, Any],
    staleness: Dict[str, Any],
    has_conflict: bool,
    now_utc: Any,
) -> Dict[str, Any]:
    score = 100
    reasons: List[str] = []
    required_fields = ["symbol", "exchange", "segment", "instrument_type", "isin", "trading_symbol"]
    completeness_score = int(sum(1 for field in required_fields if instrument.get(field)) / len(required_fields) * 100)
    if completeness_score < 100:
        score -= 20
        reasons.append("Instrument record is incomplete.")
    mapping_statuses = {str(item.get("mapping_status") or "MISSING") for item in mapping_rows}
    if "CONFLICT" in mapping_statuses or has_conflict:
        score -= 50
        reasons.append("Conflict detected in master data.")
    elif "MISSING" in mapping_statuses:
        score -= 20
        reasons.append("Broker mapping missing.")
    elif "STALE" in mapping_statuses:
        score -= 15
        reasons.append("Broker mapping stale.")
    elif "PARTIAL" in mapping_statuses:
        score -= 10
        reasons.append("Broker mapping partial.")
    if spread["state"] == "FAIL":
        score -= 20
        reasons.extend(spread["reasons"])
    elif spread["state"] == "WARN":
        score -= 10
        reasons.extend(spread["reasons"])
    if staleness["state"] in {"STALE", "EXPIRED"}:
        score -= 25
        reasons.append(f"Quote is {staleness['state'].lower()}.")
    elif staleness["state"] == "NOT_READY":
        score -= 40
        reasons.append("Quote timing not ready.")
    if float(quote.get("ltp") or 0) <= 0:
        score -= 25
        reasons.append("Invalid last traded price.")
    if float(quote.get("high") or 0) < float(quote.get("low") or 0):
        score -= 30
        reasons.append("High-low range is inconsistent.")
    if int(quote.get("volume") or 0) < 0:
        score -= 30
        reasons.append("Negative volume detected.")
    score = max(min(score, 100), 0)
    if staleness["state"] == "NOT_READY":
        quality_class = "NOT_READY"
    elif score >= 90:
        quality_class = "CONFIRMED"
    elif score >= 70:
        quality_class = "PARTIAL"
    elif score >= 55:
        quality_class = "SINGLE_SOURCE"
    elif score >= 35:
        quality_class = "SUSPECT"
    else:
        quality_class = "FAILED"
    return {
        "quality_score": score,
        "quality_class": quality_class,
        "reasons": reasons or ["Data set is consistent."],
        "completeness_score": completeness_score,
    }
