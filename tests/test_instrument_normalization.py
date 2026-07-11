import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.instruments.normalization import alias_match, dedupe_key, names_conflict, normalize_company_name, normalize_symbol


def test_normalized_company_name_fallback_and_aliases():
    assert normalize_company_name("Reliance Industries Limited") == "reliance"
    assert alias_match("Zen Energy Company", "Zen Energy Limited") is True
    assert dedupe_key("INE123", "Whatever") == "INE123"
    assert dedupe_key("", "Reliance Industries Limited") == "reliance"


def test_duplicate_symbol_conflict_helpers():
    assert normalize_symbol(" shared ") == "SHARED"
    assert names_conflict("Lotus Health Limited", "Coral Retail Limited") is True
