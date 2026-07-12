from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score, weighted_score


def compute_confidence(scores: Dict[str, float]) -> Dict[str, float]:
    value = weighted_score(
        {
            "trend": (scores["trend_score"], 1.15),
            "momentum": (scores["momentum_score"], 1.1),
            "volume": (scores["volume_score"], 0.9),
            "liquidity": (scores["liquidity_score"], 1.0),
            "institutional": (scores["institutional_score"], 0.7),
            "sector": (scores["sector_score"], 0.8),
            "relative_strength": (scores["relative_strength_score"], 1.0),
            "breakout": (scores["breakout_score"], 0.8),
            "pullback": (scores["pullback_score"], 0.5),
            "risk": (scores["risk_score"], 1.25),
            "corporate_event": (scores["corporate_event_score"], 0.45),
            "news": (scores["news_score"], 0.45),
        }
    )
    return {"ai_confidence": clamp_score(value), "final_score": clamp_score((value + scores["risk_score"]) / 2.0)}
