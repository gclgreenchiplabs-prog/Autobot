from __future__ import annotations

from typing import Dict


def compute_atr(quote: Dict[str, object]) -> float:
    high = float(quote.get("high") or 0.0)
    low = float(quote.get("low") or 0.0)
    previous_close = float(quote.get("previous_close") or 0.0)
    return round(max(high - low, abs(high - previous_close), abs(low - previous_close)), 2)
