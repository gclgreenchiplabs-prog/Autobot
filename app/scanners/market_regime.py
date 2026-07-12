from __future__ import annotations

from typing import Dict, Iterable, List


def detect_market_regime(rows: Iterable[Dict[str, object]], corporate_watch_count: int = 0) -> Dict[str, object]:
    data = list(rows)
    if not data:
        return {"regime": "RANGE", "reasons": ["No scanner inputs available."], "score": 50.0}
    avg_change = sum(float(item.get("change_pct", 0.0)) for item in data) / len(data)
    avg_atr_pct = sum(float(item.get("atr_pct", 0.0)) for item in data) / len(data)
    avg_gap = sum(float(item.get("gap_pct", 0.0)) for item in data) / len(data)
    illiquid = sum(1 for item in data if str(item.get("liquidity_class")) in {"LOW", "ILLIQUID"})
    positive = sum(1 for item in data if float(item.get("change_pct", 0.0)) > 0)
    negative = len(data) - positive
    reasons: List[str] = [
        f"avg_change_pct={avg_change:.2f}",
        f"avg_atr_pct={avg_atr_pct:.2f}",
        f"avg_gap_pct={avg_gap:.2f}",
    ]
    if corporate_watch_count:
        reasons.append(f"corporate_watch={corporate_watch_count}")
    if avg_gap >= 0.75:
        regime = "GAP_UP"
    elif avg_gap <= -0.75:
        regime = "GAP_DOWN"
    elif illiquid >= max(2, len(data) // 3):
        regime = "LOW_LIQUIDITY"
    elif avg_atr_pct >= 3.5:
        regime = "VOLATILE"
    elif positive >= max(3, int(len(data) * 0.65)) and avg_change > 0.35:
        regime = "TRENDING_BULL"
    elif negative >= max(3, int(len(data) * 0.65)) and avg_change < -0.35:
        regime = "TRENDING_BEAR"
    elif corporate_watch_count >= max(1, len(data) // 5):
        regime = "EVENT_DRIVEN"
    else:
        regime = "RANGE"
    return {"regime": regime, "reasons": reasons, "score": round(50.0 + avg_change * 10.0 + avg_atr_pct * 4.0, 2)}
