from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def evaluate_news_sentiment(symbol: str, sentiment: Dict[str, object] | None) -> Dict[str, object]:
    if not sentiment:
        return {"score": 55.0, "label": "UNKNOWN", "reason": f"No news framework sentiment for {symbol}."}
    label = str(sentiment.get("sentiment") or "UNKNOWN").upper()
    reason = str(sentiment.get("reason") or f"News sentiment for {symbol} is {label}.")
    score = {
        "POSITIVE": 82.0,
        "NEUTRAL": 58.0,
        "NEGATIVE": 22.0,
        "UNKNOWN": 55.0,
    }.get(label, 55.0)
    return {"score": clamp_score(score), "label": label, "reason": reason}
