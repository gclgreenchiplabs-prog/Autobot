from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def evaluate_vwap(price: float, vwap: float) -> Dict[str, object]:
    if vwap <= 0:
        return {"bias": "NEUTRAL", "score": 50.0}
    delta_pct = ((price - vwap) / vwap) * 100.0
    bias = "ABOVE" if delta_pct > 0.15 else "BELOW" if delta_pct < -0.15 else "AT"
    return {"bias": bias, "score": clamp_score(50.0 + (delta_pct * 12.0))}
