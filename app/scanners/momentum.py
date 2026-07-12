from __future__ import annotations

from app.scanners.ranking import clamp_score


def evaluate_momentum(change_pct: float, rsi: float, adx: float, vwap_score: float) -> float:
    return clamp_score((50.0 + (change_pct * 9.0) + ((rsi - 50.0) * 0.65) + ((adx - 20.0) * 0.75) + ((vwap_score - 50.0) * 0.35)) / 2.0)
