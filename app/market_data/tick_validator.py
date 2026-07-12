from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.instruments.repository import InstrumentRepository
from app.settings import Settings


class TickValidator:
    def __init__(self, settings: Settings, instrument_repository: InstrumentRepository) -> None:
        self.settings = settings
        self.instrument_repository = instrument_repository

    def fingerprint(self, tick: Dict[str, Any]) -> str:
        payload = {
            "instrument_id": tick["instrument_id"],
            "source": tick["source"],
            "timestamp_utc": tick["timestamp_utc"],
            "ltp": tick.get("ltp"),
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "volume": tick.get("volume"),
            "sequence_number": tick.get("sequence_number"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def validate(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        reasons: List[str] = []
        state = "VALID"
        instrument = self.instrument_repository.get_instrument(tick["instrument_id"])
        if instrument is None:
            return {"state": "UNMAPPED", "reasons": ["instrument_id not found"], "fingerprint": self.fingerprint(tick)}

        mappings = [item for item in self.instrument_repository.list_mappings() if item["instrument_id"] == tick["instrument_id"] and item["broker"] == tick["source"]]
        if tick["source"] != "fixture" and not mappings:
            return {"state": "UNMAPPED", "reasons": ["source mapping not found"], "fingerprint": self.fingerprint(tick)}

        tick_time = datetime.fromisoformat(str(tick["timestamp_utc"]).replace("Z", "+00:00")).astimezone(timezone.utc)
        received = datetime.fromisoformat(str(tick["timestamp_received"]).replace("Z", "+00:00")).astimezone(timezone.utc)
        age = (received - tick_time).total_seconds()
        if age > self.settings.max_quote_age_seconds:
            state = "STALE"
            reasons.append(f"quote age {age:.2f}s exceeded {self.settings.max_quote_age_seconds}s")

        for field in ["ltp", "open", "high", "low", "previous_close", "bid", "ask", "traded_value", "vwap", "open_interest"]:
            value = tick.get(field)
            if value is not None and float(value) < 0:
                return {"state": "REJECTED", "reasons": [f"{field} must be non-negative"], "fingerprint": self.fingerprint(tick)}

        volume = tick.get("volume")
        if volume is not None and int(volume) < 0:
            return {"state": "REJECTED", "reasons": ["volume must be non-negative"], "fingerprint": self.fingerprint(tick)}

        bid = tick.get("bid")
        ask = tick.get("ask")
        crossed = bool((tick.get("raw_reference") or {}).get("crossed_market"))
        if bid is not None and ask is not None and bid > ask and not crossed:
            return {"state": "REJECTED", "reasons": ["bid must be <= ask unless crossed"], "fingerprint": self.fingerprint(tick)}

        high = tick.get("high")
        low = tick.get("low")
        if high is not None and low is not None and high < low:
            return {"state": "REJECTED", "reasons": ["high must be >= low"], "fingerprint": self.fingerprint(tick)}

        upper = tick.get("upper_circuit")
        lower = tick.get("lower_circuit")
        if upper is not None and lower is not None and upper < lower:
            return {"state": "REJECTED", "reasons": ["upper_circuit must be >= lower_circuit"], "fingerprint": self.fingerprint(tick)}

        return {"state": state, "reasons": reasons, "fingerprint": self.fingerprint(tick)}
