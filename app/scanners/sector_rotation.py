from __future__ import annotations

from typing import Dict, Iterable, List


def build_sector_rotation(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    sectors: Dict[str, Dict[str, float]] = {}
    for row in rows:
        sector = str(row.get("sector") or "UNKNOWN")
        item = sectors.setdefault(sector, {"count": 0.0, "score": 0.0, "change_pct": 0.0})
        item["count"] += 1.0
        proxy_score = float(row.get("sector_proxy_score", ((float(row.get("trend_score", 50.0)) + float(row.get("volume_score", 50.0))) / 2.0)))
        item["score"] += proxy_score
        item["change_pct"] += float(row.get("change_pct", 0.0))
    output: List[Dict[str, object]] = []
    for sector, item in sectors.items():
        count = max(item["count"], 1.0)
        avg_score = round(item["score"] / count, 2)
        avg_change = round(item["change_pct"] / count, 2)
        label = "LEADING" if avg_score >= 70.0 else "ROTATING" if avg_score >= 50.0 else "LAGGING"
        output.append({"sector": sector, "score": avg_score, "avg_change_pct": avg_change, "label": label, "count": int(count)})
    output.sort(key=lambda item: (float(item["score"]), float(item["avg_change_pct"])), reverse=True)
    return output
