from __future__ import annotations

from typing import Any, Dict


def evaluate_spread(quote: Dict[str, Any], max_allowed_spread_pct: float, staleness_state: str) -> Dict[str, Any]:
    bid = quote.get("bid")
    ask = quote.get("ask")
    reasons = []
    if bid in {None, ""} or ask in {None, ""}:
        return {"state": "NOT_READY", "absolute_spread": None, "spread_pct": None, "reasons": ["Missing bid or ask."]}
    bid = float(bid)
    ask = float(ask)
    if bid > ask:
        return {"state": "FAIL", "absolute_spread": ask - bid, "spread_pct": None, "reasons": ["Crossed market detected."]}
    midpoint = (bid + ask) / 2
    if midpoint <= 0:
        return {"state": "NOT_READY", "absolute_spread": ask - bid, "spread_pct": None, "reasons": ["Zero or negative midpoint."]}
    absolute_spread = ask - bid
    spread_pct = (absolute_spread / midpoint) * 100
    if staleness_state in {"STALE", "EXPIRED"}:
        return {"state": "FAIL", "absolute_spread": round(absolute_spread, 4), "spread_pct": round(spread_pct, 4), "reasons": ["Quote is stale."]}
    if spread_pct > max_allowed_spread_pct:
        return {"state": "FAIL", "absolute_spread": round(absolute_spread, 4), "spread_pct": round(spread_pct, 4), "reasons": [f"Spread {spread_pct:.2f}% above threshold."]}
    if spread_pct > max_allowed_spread_pct * 0.7:
        reasons.append(f"Spread {spread_pct:.2f}% nearing threshold.")
        return {"state": "WARN", "absolute_spread": round(absolute_spread, 4), "spread_pct": round(spread_pct, 4), "reasons": reasons}
    return {"state": "PASS", "absolute_spread": round(absolute_spread, 4), "spread_pct": round(spread_pct, 4), "reasons": ["Spread within threshold."]}
