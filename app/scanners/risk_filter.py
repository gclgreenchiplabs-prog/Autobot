from __future__ import annotations

from typing import Dict

from app.scanners.ranking import clamp_score


def evaluate_risk(
    *,
    spread_pct: float,
    liquidity_class: str,
    quality_class: str,
    staleness_state: str,
    corporate_risk: str,
    news_label: str,
) -> Dict[str, object]:
    penalty = 0.0
    reasons = []
    if spread_pct > 0.5:
        penalty += 26.0
        reasons.append("spread above threshold")
    if liquidity_class in {"LOW", "ILLIQUID"}:
        penalty += 24.0
        reasons.append(f"liquidity={liquidity_class}")
    if quality_class in {"FAILED", "SUSPECT"}:
        penalty += 22.0
        reasons.append(f"quality={quality_class}")
    if staleness_state in {"STALE", "EXPIRED"}:
        penalty += 18.0
        reasons.append(f"staleness={staleness_state}")
    if corporate_risk == "HIGH":
        penalty += 18.0
        reasons.append("corporate-event risk high")
    elif corporate_risk == "MEDIUM":
        penalty += 10.0
        reasons.append("corporate-event watch")
    if news_label == "NEGATIVE":
        penalty += 18.0
        reasons.append("negative news framework sentiment")
    score = clamp_score(92.0 - penalty)
    if score >= 72.0:
        level = "LOW"
    elif score >= 52.0:
        level = "MEDIUM"
    elif score >= 32.0:
        level = "HIGH"
    else:
        level = "EXTREME"
    return {"score": score, "level": level, "reasons": reasons}
