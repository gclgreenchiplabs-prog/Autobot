from __future__ import annotations

from typing import Any, Dict, List


def evaluate_liquidity(
    quote: Dict[str, Any],
    staleness_state: str,
    *,
    min_intraday_traded_value: float,
    min_btst_traded_value: float,
    min_swing_traded_value: float,
    min_option_oi: int,
    min_option_volume: int,
    max_allowed_spread_pct: float,
    instrument_type: str,
    fno_eligible: bool,
) -> Dict[str, Any]:
    traded_value = float(quote.get("traded_value") or 0.0)
    volume = int(quote.get("volume") or 0)
    bid_quantity = int(quote.get("bid_quantity") or 0)
    ask_quantity = int(quote.get("ask_quantity") or 0)
    bid = quote.get("bid")
    ask = quote.get("ask")
    spread_pct = 100.0
    if bid not in {None, ""} and ask not in {None, ""}:
        midpoint = (float(bid) + float(ask)) / 2
        if midpoint > 0:
            spread_pct = ((float(ask) - float(bid)) / midpoint) * 100
    score = 0
    reasons: List[str] = []
    score += min(int(traded_value / max(min_swing_traded_value, 1) * 20), 40)
    score += min(int(volume / 5000), 20)
    score += min(int((bid_quantity + ask_quantity) / 1000), 20)
    if spread_pct <= max_allowed_spread_pct:
        score += 15
    else:
        reasons.append("Spread too wide for preferred execution.")
    if staleness_state in {"FRESH", "AGING"}:
        score += 10
    else:
        reasons.append("Quote freshness is insufficient.")
    if volume == 0 or traded_value == 0:
        reasons.append("Zero volume session.")
    score = max(min(score, 100), 0)
    if staleness_state == "NOT_READY":
        liquidity_class = "NOT_READY"
    elif score >= 75:
        liquidity_class = "HIGH"
    elif score >= 55:
        liquidity_class = "MEDIUM"
    elif score >= 35:
        liquidity_class = "LOW"
    else:
        liquidity_class = "ILLIQUID"
    return {
        "liquidity_score": score,
        "liquidity_class": liquidity_class,
        "reasons": reasons or ["Liquidity is acceptable."],
        "eligible_for_intraday": traded_value >= min_intraday_traded_value and spread_pct <= max_allowed_spread_pct and staleness_state in {"FRESH", "AGING"},
        "eligible_for_btst": traded_value >= min_btst_traded_value and staleness_state in {"FRESH", "AGING", "STALE"},
        "eligible_for_swing": traded_value >= min_swing_traded_value,
        "eligible_for_options": bool(fno_eligible and instrument_type == "OPTION" and int(quote.get("open_interest") or 0) >= min_option_oi and volume >= min_option_volume),
    }
