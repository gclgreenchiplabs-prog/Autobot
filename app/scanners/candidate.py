from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class CandidateRecord:
    candidate_id: str
    company_id: str
    instrument_id: str
    symbol: str
    exchange: str
    direction: str
    instrument_type: str
    strategy_scope: str
    score: float
    confidence: float
    liquidity_score: float
    data_quality_score: float
    fno_eligible: bool
    preferred_exchange: str
    data_mode: str
    eligible: bool
    rejection_reasons_json: List[str] = field(default_factory=list)
    selection_reasons_json: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
