from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompanyRecord:
    company_id: str
    company_name: str
    isin: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap_category: Optional[str]
    active: bool
    created_at: str
    updated_at: str
    preferred_exchange: Optional[str] = None
    selection_score: float = 0.0
    selection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InstrumentRecord:
    instrument_id: str
    company_id: str
    exchange: str
    segment: str
    symbol: str
    trading_symbol: str
    exchange_token: Optional[str]
    broker: Optional[str]
    broker_symbol: Optional[str]
    broker_security_id: Optional[str]
    isin: Optional[str]
    instrument_type: str
    underlying_symbol: Optional[str]
    expiry: Optional[str]
    strike: Optional[float]
    option_type: Optional[str]
    lot_size: int
    tick_size: float
    price_precision: int
    fno_eligible: bool
    cash_eligible: bool
    bse_code: Optional[str]
    nse_symbol: Optional[str]
    currency: str
    active: bool
    listing_date: Optional[str]
    delisting_date: Optional[str]
    last_updated: str
    preferred_exchange: Optional[str] = None
    selection_score: float = 0.0
    selection_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrokerInstrumentMappingRecord:
    mapping_id: str
    instrument_id: str
    company_id: str
    exchange: str
    segment: str
    broker: str
    broker_symbol: Optional[str]
    broker_security_id: Optional[str]
    exchange_token: Optional[str]
    trading_symbol: Optional[str]
    instrument_type: Optional[str]
    expiry: Optional[str]
    strike: Optional[float]
    option_type: Optional[str]
    lot_size: Optional[int]
    mapping_status: str
    last_verified_timestamp: Optional[str]
    active: bool
    conflict_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InstrumentConflictRecord:
    conflict_id: str
    conflict_type: str
    symbol: Optional[str]
    isin: Optional[str]
    brokers_involved: List[str]
    reason: str
    resolution_status: str
    payload_json: Dict[str, Any]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InstrumentImportRunRecord:
    run_id: str
    source: str
    source_version: str
    checksum: str
    row_count: int
    validation_status: str
    import_timestamp: str
    last_successful_refresh: Optional[str]
    completed_at: Optional[str]
    metadata_json: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UniverseStatusRecord:
    total_companies: int
    total_instruments: int
    nse_count: int
    bse_count: int
    fno_count: int
    active_count: int
    conflict_count: int
    last_import_time: Optional[str]
    import_source: str
    source_version: Optional[str]
    migration_version: str
    broker_mapping_summary: Dict[str, Dict[str, int]]
    quality_class_counts: Dict[str, int]
    liquidity_class_counts: Dict[str, int]
    stale_state_counts: Dict[str, int]
    ready: bool
    selection_summary: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
