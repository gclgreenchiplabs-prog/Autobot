from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def evaluate_volume(quote: Dict[str, object], liquidity_score: float) -> Dict[str, object]:
    traded_value = float(quote.get("traded_value") or 0.0)
    volume = float(quote.get("volume") or 0.0)
    score = clamp_score((traded_value / 2_000_000.0) + (volume / 2500.0) + (float(liquidity_score) * 0.35))
    label = "EXPANSION" if score >= 72.0 else "STEADY" if score >= 45.0 else "LIGHT"
    return {"score": score, "label": label}
