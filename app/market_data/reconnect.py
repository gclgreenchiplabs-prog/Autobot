from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict


@dataclass
class ReconnectState:
    attempt: int = 0
    delay_seconds: float = 0.0
    cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReconnectPolicy:
    def __init__(
        self,
        *,
        initial_seconds: float,
        max_seconds: float,
        max_attempts: int,
        jitter_fn: Callable[[int], float] | None = None,
    ) -> None:
        self.initial_seconds = initial_seconds
        self.max_seconds = max_seconds
        self.max_attempts = max_attempts
        self.jitter_fn = jitter_fn or (lambda attempt: 0.0)
        self.state = ReconnectState()

    def next_delay(self) -> float | None:
        if self.state.cancelled:
            return None
        if self.state.attempt >= self.max_attempts:
            return None
        self.state.attempt += 1
        base = min(self.initial_seconds * (2 ** (self.state.attempt - 1)), self.max_seconds)
        self.state.delay_seconds = min(base + self.jitter_fn(self.state.attempt), self.max_seconds)
        return self.state.delay_seconds

    def reset(self) -> None:
        self.state = ReconnectState()

    def cancel(self) -> None:
        self.state.cancelled = True
