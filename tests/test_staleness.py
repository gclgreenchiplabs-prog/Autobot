import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.market_data.staleness import evaluate_staleness


def test_staleness_states():
    now = datetime.now(timezone.utc)
    fresh = evaluate_staleness(
        timestamp_utc=(now - timedelta(seconds=5)).isoformat(),
        import_timestamp=now.isoformat(),
        mapping_age_hours=1,
        now_utc=now,
        quote_fresh_seconds=10,
        quote_aging_seconds=30,
        instrument_master_max_age_hours=24,
        broker_mapping_max_age_hours=24,
        data_mode="FIXTURE",
    )
    stale = evaluate_staleness(
        timestamp_utc=(now - timedelta(seconds=80)).isoformat(),
        import_timestamp=now.isoformat(),
        mapping_age_hours=1,
        now_utc=now,
        quote_fresh_seconds=10,
        quote_aging_seconds=30,
        instrument_master_max_age_hours=24,
        broker_mapping_max_age_hours=24,
        data_mode="FIXTURE",
    )
    assert fresh["state"] == "FRESH"
    assert stale["state"] in {"STALE", "EXPIRED"}
