from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional


class SequenceTracker:
    def __init__(self) -> None:
        self._state: Dict[tuple[str, str], Dict[str, Any]] = defaultdict(dict)

    def evaluate(self, tick: Dict[str, Any], *, fingerprint: str) -> Dict[str, Any]:
        key = (tick["source"], tick["instrument_id"])
        current = self._state.get(key, {})
        sequence = tick.get("sequence_number")
        timestamp_utc = tick["timestamp_utc"]
        previous_sequence = current.get("sequence_number")
        previous_fingerprint = current.get("fingerprint")
        previous_timestamp = current.get("timestamp_utc")

        if previous_fingerprint == fingerprint:
            return {"state": "DUPLICATE", "reason": "payload fingerprint matched previous tick"}

        if sequence is None:
            self._state[key] = {"sequence_number": None, "timestamp_utc": timestamp_utc, "fingerprint": fingerprint}
            if previous_timestamp and timestamp_utc < previous_timestamp:
                return {"state": "OUT_OF_ORDER", "reason": "timestamp decreased without sequence support"}
            return {"state": "VALID", "reason": "source does not provide sequence"}

        if previous_sequence is None:
            self._state[key] = {"sequence_number": sequence, "timestamp_utc": timestamp_utc, "fingerprint": fingerprint}
            return {"state": "VALID", "reason": "first sequenced tick"}

        if sequence == previous_sequence:
            return {"state": "DUPLICATE", "reason": "sequence number repeated"}
        if sequence < previous_sequence:
            self._state[key] = {"sequence_number": sequence, "timestamp_utc": timestamp_utc, "fingerprint": fingerprint}
            return {"state": "OUT_OF_ORDER", "reason": f"sequence decreased from {previous_sequence} to {sequence}"}
        if sequence > previous_sequence + 1:
            self._state[key] = {"sequence_number": sequence, "timestamp_utc": timestamp_utc, "fingerprint": fingerprint}
            return {"state": "WARNING", "reason": f"sequence gap from {previous_sequence} to {sequence}", "gap": sequence - previous_sequence}

        self._state[key] = {"sequence_number": sequence, "timestamp_utc": timestamp_utc, "fingerprint": fingerprint}
        return {"state": "VALID", "reason": "sequence advanced normally"}

    def reset_source(self, source: str) -> None:
        for key in list(self._state.keys()):
            if key[0] == source:
                del self._state[key]

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {f"{source}:{instrument_id}": dict(value) for (source, instrument_id), value in self._state.items()}
