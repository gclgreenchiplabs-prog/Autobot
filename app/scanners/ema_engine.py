from __future__ import annotations

from typing import Dict


def compute_emas(price: float, vwap: float, previous_close: float) -> Dict[str, float]:
    anchor = (price + vwap + previous_close) / 3.0 if previous_close > 0 else max(price, vwap, 0.01)
    ema20 = round((price * 0.55) + (vwap * 0.3) + (anchor * 0.15), 2)
    ema50 = round((price * 0.3) + (vwap * 0.35) + (anchor * 0.35), 2)
    ema200 = round((price * 0.15) + (vwap * 0.25) + (anchor * 0.6), 2)
    return {"ema20": ema20, "ema50": ema50, "ema200": ema200}
