from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from app.settings import Settings


def _round_money(value: float) -> float:
    return round(float(value), 2)


@dataclass(frozen=True)
class ChargeBreakdown:
    turnover: float
    brokerage: float
    stt: float
    exchange_txn: float
    sebi: float
    gst: float
    stamp_duty: float
    total: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "turnover": self.turnover,
            "brokerage": self.brokerage,
            "stt": self.stt,
            "exchange_txn": self.exchange_txn,
            "sebi": self.sebi,
            "gst": self.gst,
            "stamp_duty": self.stamp_duty,
            "total": self.total,
        }


class BrokerChargesCalculator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def calculate(self, *, price: float, quantity: int, side: str) -> ChargeBreakdown:
        turnover = max(float(price), 0.0) * max(int(quantity), 0)
        normalized_side = str(side or "BUY").strip().upper()

        brokerage_value = max(
            turnover * (self.settings.brokerage_pct / 100.0),
            self.settings.brokerage_flat_per_order if turnover > 0 else 0.0,
        )
        exchange_txn = turnover * (self.settings.exchange_txn_pct / 100.0)
        sebi = turnover * (self.settings.sebi_charges_pct / 100.0)
        stt = turnover * (self.settings.stt_sell_pct / 100.0) if normalized_side in {"SELL", "SHORT"} else 0.0
        stamp_duty = turnover * (self.settings.stamp_duty_buy_pct / 100.0) if normalized_side == "BUY" else 0.0
        gst_taxable = brokerage_value + exchange_txn + sebi
        gst = gst_taxable * (self.settings.gst_pct / 100.0)
        total = brokerage_value + exchange_txn + sebi + stt + stamp_duty + gst

        return ChargeBreakdown(
            turnover=_round_money(turnover),
            brokerage=_round_money(brokerage_value),
            stt=_round_money(stt),
            exchange_txn=_round_money(exchange_txn),
            sebi=_round_money(sebi),
            gst=_round_money(gst),
            stamp_duty=_round_money(stamp_duty),
            total=_round_money(total),
        )

    def estimate_round_trip(self, *, entry_price: float, exit_price: float, quantity: int, side: str) -> Dict[str, Any]:
        entry = self.calculate(price=entry_price, quantity=quantity, side=side)
        exit_side = "SELL" if str(side or "BUY").strip().upper() in {"BUY", "LONG"} else "BUY"
        exit_charge = self.calculate(price=exit_price, quantity=quantity, side=exit_side)
        return {
            "entry": entry.to_dict(),
            "exit": exit_charge.to_dict(),
            "total": _round_money(entry.total + exit_charge.total),
        }
