from __future__ import annotations

from typing import Dict, Iterable, List

from app.scanners.earnings_filter import normalize_earnings_event
from app.scanners.ranking import clamp_score


def evaluate_corporate_events(symbol: str, events: Iterable[Dict[str, object]]) -> Dict[str, object]:
    rows = list(events)
    if not rows:
        return {"score": 60.0, "risk": "CLEAR", "events": [], "reason": "No corporate-event framework entries for the symbol."}
    normalized: List[Dict[str, object]] = []
    risk_penalty = 0.0
    risk = "LOW"
    for event in rows:
        label = str(event.get("event_type") or event.get("label") or "UNKNOWN").upper()
        severity = str(event.get("severity") or "INFO").upper()
        impact = str(event.get("impact") or "NEUTRAL").upper()
        earnings = normalize_earnings_event(event)
        normalized.append({**event, "label": label, "severity": severity, "impact": impact, **earnings})
        if impact in {"NEGATIVE", "HIGH_RISK"} or severity in {"ERROR", "CRITICAL"}:
            risk_penalty += 32.0
            risk = "HIGH"
        elif impact in {"WATCH", "MEDIUM_RISK"} or earnings["is_earnings_related"]:
            risk_penalty += 18.0
            risk = "MEDIUM" if risk != "HIGH" else risk
        else:
            risk_penalty += 6.0
    score = clamp_score(82.0 - risk_penalty)
    return {"score": score, "risk": risk, "events": normalized, "reason": f"{len(rows)} framework event(s) attached to {symbol}."}
