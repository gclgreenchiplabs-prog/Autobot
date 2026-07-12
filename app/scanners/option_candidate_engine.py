from __future__ import annotations

from typing import Dict, List


def option_categories(profile: Dict[str, object]) -> List[str]:
    if str(profile.get("instrument_type")) != "OPTION":
        return []
    if not bool(profile.get("eligible")):
        return ["avoid"]
    categories = ["options"]
    if str(profile.get("risk_level")) in {"HIGH", "EXTREME"}:
        categories.append("high_risk")
    if str(profile.get("decision")) in {"WATCH", "WAIT"}:
        categories.append("watchlist")
    return categories
