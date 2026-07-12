from __future__ import annotations

from app.scanners.ranking import clamp_score


def evaluate_relative_strength(change_pct: float, sector_change_pct: float, market_change_pct: float) -> float:
    return clamp_score(50.0 + (change_pct - market_change_pct) * 8.0 + (change_pct - sector_change_pct) * 6.0)
