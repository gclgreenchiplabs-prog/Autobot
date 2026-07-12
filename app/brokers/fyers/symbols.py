from __future__ import annotations

from typing import Any, Dict, Optional

from app.instruments.repository import InstrumentRepository


def resolve_fyers_symbol(repository: InstrumentRepository, instrument_id: str) -> Optional[Dict[str, Any]]:
    for mapping in repository.list_mappings():
        if mapping["instrument_id"] == instrument_id and mapping["broker"] == "fyers":
            return mapping
    return None
