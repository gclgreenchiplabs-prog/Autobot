from __future__ import annotations

from app.scanners.ranking import clamp_score


def compute_rsi(price: float, previous_close: float, vwap: float) -> float:
    if previous_close <= 0:
        return 50.0
    change_pct = ((price - previous_close) / previous_close) * 100.0
    vwap_bias = ((price - vwap) / vwap) * 100.0 if vwap > 0 else 0.0
    return clamp_score(50.0 + (change_pct * 4.2) + (vwap_bias * 2.1), 5.0, 95.0)
