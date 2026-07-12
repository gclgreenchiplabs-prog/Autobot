from __future__ import annotations

from typing import Dict, Iterable, List


def build_reasoning_lines(metrics: Dict[str, object], extra_reasons: Iterable[str]) -> List[str]:
    reasons = [
        f"Trend {metrics['trend']} with RSI {metrics['rsi']} and ADX {metrics['adx']}.",
        f"Liquidity {metrics['liquidity_class']} and spread {metrics['spread_pct']}%.",
        f"Gap {metrics['gap_pct']}% with VWAP bias {metrics['vwap_bias']}.",
        f"Corporate risk {metrics['corporate_risk']} and news {metrics['news_label']}.",
    ]
    reasons.extend(reason for reason in extra_reasons if reason)
    return reasons
