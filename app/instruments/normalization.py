from __future__ import annotations

import re
from typing import Dict, Iterable, Optional


_SUFFIXES = (
    "limited",
    "ltd",
    "private",
    "pvt",
    "industries",
    "industry",
    "company",
    "co",
    "corp",
    "corporation",
)

EXPLICIT_ALIAS_MAP: Dict[str, str] = {
    "reliance ind": "reliance",
    "zen energy company": "zen energy",
}


def normalize_company_name(name: Optional[str]) -> str:
    if not name:
        return ""
    normalized = re.sub(r"[^A-Za-z0-9 ]+", " ", name).lower()
    tokens = [token for token in normalized.split() if token and token not in _SUFFIXES]
    collapsed = " ".join(tokens)
    return EXPLICIT_ALIAS_MAP.get(collapsed, collapsed)


def normalize_symbol(symbol: Optional[str]) -> str:
    if not symbol:
        return ""
    return re.sub(r"[^A-Za-z0-9]+", "", symbol).upper()


def dedupe_key(isin: Optional[str], company_name: Optional[str]) -> str:
    normalized_isin = (isin or "").strip().upper()
    if normalized_isin:
        return normalized_isin
    return normalize_company_name(company_name)


def names_conflict(name_a: Optional[str], name_b: Optional[str]) -> bool:
    normalized_a = normalize_company_name(name_a)
    normalized_b = normalize_company_name(name_b)
    return bool(normalized_a and normalized_b and normalized_a != normalized_b)


def alias_match(name_a: Optional[str], name_b: Optional[str]) -> bool:
    normalized_a = normalize_company_name(name_a)
    normalized_b = normalize_company_name(name_b)
    return normalized_a == normalized_b


def dedupe_by_alias_or_name(names: Iterable[str]) -> str:
    normalized = [normalize_company_name(name) for name in names if name]
    return normalized[0] if normalized else ""
