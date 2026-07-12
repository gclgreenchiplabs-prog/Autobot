from __future__ import annotations

from app.scanners.ranking import clamp_score


def evaluate_breakout(price: float, high: float, previous_close: float, vwap: float) -> float:
    if high <= 0:
        return 45.0
    high_distance_pct = ((high - price) / high) * 100.0
    support = 8.0 if price > previous_close and price > vwap else -6.0
    return clamp_score(82.0 - (high_distance_pct * 14.0) + support)
