import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.instruments.models import CompanyRecord, InstrumentRecord


def test_company_and_instrument_models_round_trip():
    company = CompanyRecord(
        company_id="cmp-001",
        company_name="Reliance Industries Limited",
        isin="INE002A01018",
        sector="Energy",
        industry="Integrated Oil & Gas",
        market_cap_category="LARGE_CAP",
        active=True,
        created_at="2026-07-12T00:00:00+00:00",
        updated_at="2026-07-12T00:00:00+00:00",
    )
    instrument = InstrumentRecord(
        instrument_id="NSE:CASH:RELIANCE",
        company_id="cmp-001",
        exchange="NSE",
        segment="CASH",
        symbol="RELIANCE",
        trading_symbol="RELIANCE",
        exchange_token="2885",
        broker="fyers",
        broker_symbol="NSE:RELIANCE-EQ",
        broker_security_id="1333",
        isin="INE002A01018",
        instrument_type="EQUITY",
        underlying_symbol="RELIANCE",
        expiry=None,
        strike=None,
        option_type=None,
        lot_size=1,
        tick_size=0.05,
        price_precision=2,
        fno_eligible=True,
        cash_eligible=True,
        bse_code=None,
        nse_symbol="RELIANCE",
        currency="INR",
        active=True,
        listing_date="1995-01-01",
        delisting_date=None,
        last_updated="2026-07-12T00:00:00+00:00",
    )
    assert company.to_dict()["isin"] == "INE002A01018"
    assert instrument.to_dict()["segment"] == "CASH"
