from __future__ import annotations

from app.scanners.ranking import clamp_score


def compute_adx(price: float, vwap: float, atr: float) -> float:
    if atr <= 0:
        return 12.0
    trend_distance = abs(price - vwap) / atr
    return clamp_score(12.0 + (trend_distance * 28.0), 8.0, 60.0)
