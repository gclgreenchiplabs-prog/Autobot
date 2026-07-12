from __future__ import annotations

from app.scanners.ranking import clamp_score


def evaluate_pullback(price: float, ema20: float, ema50: float, high: float) -> float:
    if ema20 <= 0 or ema50 <= 0:
        return 40.0
    support_bonus = 16.0 if price >= ema20 >= ema50 else 8.0 if price >= ema50 else -10.0
    off_high_pct = ((high - price) / high) * 100.0 if high > 0 else 0.0
    return clamp_score(58.0 + support_bonus - (off_high_pct * 8.0))
