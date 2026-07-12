from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def compute_gap(quote: Dict[str, object]) -> Dict[str, object]:
    previous_close = float(quote.get("previous_close") or 0.0)
    open_price = float(quote.get("open") or 0.0)
    if previous_close <= 0:
        return {"gap_pct": 0.0, "label": "FLAT", "score": 50.0}
    gap_pct = ((open_price - previous_close) / previous_close) * 100.0
    label = "GAP_UP" if gap_pct > 0.35 else "GAP_DOWN" if gap_pct < -0.35 else "FLAT"
    return {"gap_pct": round(gap_pct, 2), "label": label, "score": clamp_score(50.0 + (gap_pct * 6.0))}
