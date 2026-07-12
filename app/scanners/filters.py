from __future__ import annotations

from typing import Dict, List


def candidate_buckets(profile: Dict[str, object]) -> List[str]:
    categories: List[str] = []
    if str(profile.get("instrument_type")) == "OPTION":
        return categories
    if bool(profile.get("intraday_eligible")) and str(profile.get("decision")) in {"BUY", "WATCH", "WAIT", "REDUCE SIZE"}:
        categories.append("intraday")
    if bool(profile.get("btst_eligible")) and str(profile.get("decision")) != "NO TRADE":
        categories.append("btst")
    if bool(profile.get("swing_eligible")) and str(profile.get("decision")) != "NO TRADE":
        categories.append("swing")
    if str(profile.get("instrument_type")) in {"EQUITY", "ETF"} and str(profile.get("decision")) not in {"AVOID", "NO TRADE"}:
        categories.append("portfolio")
    if str(profile.get("direction")) == "SHORT" and float(profile.get("final_score", 0.0)) >= 55.0:
        categories.append("short")
    if str(profile.get("decision")) in {"WATCH", "WAIT", "REDUCE SIZE"}:
        categories.append("watchlist")
    if str(profile.get("decision")) in {"AVOID", "NO TRADE"} or not bool(profile.get("eligible")):
        categories.append("avoid")
    if str(profile.get("risk_level")) in {"HIGH", "EXTREME"}:
        categories.append("high_risk")
    if str(profile.get("corporate_risk")) in {"MEDIUM", "HIGH"}:
        categories.append("corporate_watchlist")
    return categories
