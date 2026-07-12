from __future__ import annotations

from typing import Dict


EARNINGS_EVENT_TYPES = {"RESULTS", "BOARD_MEETING", "DIVIDEND", "AGM"}


def normalize_earnings_event(event: Dict[str, object]) -> Dict[str, object]:
    label = str(event.get("event_type") or event.get("label") or "UNKNOWN").upper()
    return {"is_earnings_related": label in EARNINGS_EVENT_TYPES, "label": label}
