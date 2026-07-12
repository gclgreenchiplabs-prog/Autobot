from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def evaluate_delivery(instrument: Dict[str, object], quote: Dict[str, object]) -> Dict[str, object]:
    traded_value = float(quote.get("traded_value") or 0.0)
    market_cap = str(instrument.get("market_cap_category") or "").upper()
    market_cap_bonus = {"LARGE_CAP": 16.0, "MID_CAP": 10.0, "SMALL_CAP": 4.0}.get(market_cap, 6.0)
    fno_bonus = 10.0 if instrument.get("fno_eligible") else 0.0
    score = clamp_score((traded_value / 2_500_000.0) + market_cap_bonus + fno_bonus + 18.0)
    label = "INSTITUTIONAL" if score >= 75.0 else "MIXED" if score >= 50.0 else "RETAIL"
    return {"score": score, "label": label}
