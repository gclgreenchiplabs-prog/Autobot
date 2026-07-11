import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.instruments.mapper import resolve_mapping_status


def test_fyers_and_dhan_mapping_states():
    fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    stale = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    assert resolve_mapping_status(broker="fyers", broker_symbol="NSE:RELIANCE-EQ", broker_security_id=None, exchange_token="2885", last_verified_timestamp=fresh) == "READY"
    assert resolve_mapping_status(broker="dhan", broker_symbol=None, broker_security_id=None, exchange_token=None, last_verified_timestamp=None) == "MISSING"
    assert resolve_mapping_status(broker="dhan", broker_symbol="TCS", broker_security_id="123", exchange_token=None, last_verified_timestamp=stale) == "STALE"
    assert resolve_mapping_status(broker="dhan", broker_symbol="TCS", broker_security_id="123", exchange_token=None, last_verified_timestamp=fresh, conflict=True) == "CONFLICT"
