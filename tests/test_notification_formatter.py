import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.notifications.formatter import NotificationFormatter
from app.notifications.models import NotificationRecord, NotificationType


def make_record(notification_type: str, **payload):
    return NotificationRecord.create(notification_type, payload=payload)


def test_signal_formatting():
    formatter = NotificationFormatter()
    record = make_record(
        NotificationType.SIGNAL_GENERATED.value,
        symbol="RELIANCE",
        option_type="CE",
        strike=3000,
        expiry="30-Jul-2026",
        strategy="Intraday Momentum",
        side="BUY",
        quantity=500,
        lots=2,
        entry_price=41.60,
        initial_stop=36.80,
        t1=48.50,
        t2=56.00,
        t3=67.50,
        stretch_target=83.00,
        capital_used_trade=20800.0,
        capital_available=478500.0,
        reason="VWAP breakout",
        payload_json={
            "direction": "CE BUY",
            "confidence": "84%",
            "entry_zone": "₹41.20-₹42.00",
            "preferred_entry": 41.60,
            "sl": 36.80,
            "base_rr": "1:2.1",
            "stretch_rr": "1:8.6",
            "estimated_capital": 20800.0,
            "invalidation_condition": "Underlying closes below VWAP.",
        },
    )
    formatted = formatter.format(record)
    assert "SIGNAL GENERATED" in formatted["title"]
    assert "RELIANCE" in formatted["body"]
    assert "VWAP breakout" in formatted["body"]


def test_order_and_fill_formatting():
    formatter = NotificationFormatter()
    submitted = make_record(
        NotificationType.ORDER_SUBMITTED.value,
        trade_id="trade-1",
        symbol="RELIANCE",
        expiry="30-Jul-2026",
        strike=3000,
        side="BUY",
        quantity=500,
        capital_used_trade=20800.0,
        capital_reserved=20800.0,
        capital_available=457700.0,
        payload_json={
            "broker": "paper",
            "idempotency_key": "idem-1",
            "order_type": "LIMIT",
            "requested_price": 41.60,
            "capital_before_submission": 478500.0,
        },
    )
    filled = make_record(
        NotificationType.ORDER_FILLED.value,
        symbol="RELIANCE",
        broker_order_id="broker-1",
        quantity=500,
        entry_price=41.80,
        initial_stop=36.80,
        t1=48.50,
        t2=56.00,
        t3=67.50,
        capital_used_trade=20900.0,
        capital_available=457600.0,
        position_status="OPEN",
        payload_json={
            "requested_price": 41.60,
            "average_fill_price": 41.80,
            "filled_quantity": 500,
            "fill_timestamp": "2026-07-11T09:42:18+05:30",
            "slippage": 0.20,
            "charges_estimate": 126.0,
        },
    )
    assert "ORDER SUBMITTED" in formatter.format(submitted)["body"]
    fill_body = formatter.format(filled)["body"]
    assert "ORDER FILLED" in fill_body
    assert "Average fill price" in fill_body


def test_hold_and_exit_formatting():
    formatter = NotificationFormatter()
    hold = make_record(
        NotificationType.POSITION_HOLD.value,
        symbol="RELIANCE",
        expiry="30-Jul-2026",
        entry_price=41.60,
        current_price=54.20,
        highest_price=57.10,
        current_stop=49.80,
        locked_profit=4100.0,
        trade_pnl=6300.0,
        highest_profit=7750.0,
        t1=48.50,
        t2=56.00,
        t3=67.50,
        t1_status="HIT",
        t2_status="PENDING",
        t3_status="PENDING",
        next_predicted_target=56.00,
        capital_used_trade=20800.0,
        day_total_pnl=12450.0,
        capital_available=491150.0,
        reason="Momentum remains above VWAP and volume is supportive.",
        payload_json={"exit_condition": "5-minute close below TSL."},
    )
    exited = make_record(
        NotificationType.POSITION_EXITED.value,
        symbol="RELIANCE",
        expiry="30-Jul-2026",
        strategy="Intraday Momentum",
        entry_price=41.60,
        exit_price=59.40,
        hold_duration_seconds=5794,
        t1_status="HIT",
        t2_status="HIT",
        t3_status="NOT HIT",
        highest_price=62.80,
        highest_profit=10600.0,
        current_stop=59.20,
        reason="5-minute close below trailing stop after T2.",
        trade_pnl=8900.0,
        trade_pnl_pct=41.22,
        capital_used_trade=20800.0,
        capital_released=29374.0,
        day_realized_pnl=16830.0,
        day_unrealized_pnl=3400.0,
        day_total_pnl=20230.0,
        capital_available=508730.0,
        payload_json={
            "entry_timestamp": "2026-07-11T09:42:18+05:30",
            "exit_timestamp": "2026-07-11T11:18:52+05:30",
            "charges": 326.0,
            "net_pnl": 8574.0,
            "net_pnl_pct": 41.22,
        },
    )
    assert "POSITION HOLD" in formatter.format(hold)["body"]
    exit_body = formatter.format(exited)["body"]
    assert "POSITION EXITED" in exit_body
    assert "Net P&L" in exit_body
