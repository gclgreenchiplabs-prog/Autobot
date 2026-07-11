from __future__ import annotations

from datetime import timedelta
from html import escape
from typing import Any, Dict, Iterable, List, Optional


def money(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    amount = float(value)
    sign = "+" if amount > 0 else ""
    return f"{sign}₹{amount:,.2f}"


def plain_money(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    return f"₹{float(value):,.2f}"


def pct(value: Any) -> str:
    if value is None or value == "":
        return "N/A"
    amount = float(value)
    sign = "+" if amount > 0 else ""
    return f"{sign}{amount:.2f}%"


def text(value: Any, fallback: str = "N/A") -> str:
    if value is None:
        return fallback
    content = str(value).strip()
    return content or fallback


def duration(seconds: Any) -> str:
    total_seconds = int(seconds or 0)
    human = str(timedelta(seconds=total_seconds))
    if human.startswith("0:"):
        return human[2:]
    return human


def join_lines(lines: Iterable[str]) -> str:
    return "\n".join(line for line in lines if line is not None and line != "")


def html_header(title: str) -> str:
    return f"<b>{escape(title)}</b>"


def html_label(label: str, value: Any) -> str:
    return f"<b>{escape(label)}:</b> {escape(text(value))}"


def render_status_list(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "No open positions."
    sections: List[str] = []
    for item in items:
        sections.append(
            join_lines(
                [
                    f"{text(item.get('symbol'))} {text(item.get('option_type') or item.get('instrument_type'))}",
                    f"Entry {plain_money(item.get('entry_price'))} | Current {plain_money(item.get('current_price'))}",
                    f"T1 {plain_money(item.get('t1'))}: {text(item.get('t1_status'))}",
                    f"T2 {plain_money(item.get('t2'))}: {text(item.get('t2_status'))}",
                    f"T3 {plain_money(item.get('t3'))}: {text(item.get('t3_status'))}",
                    f"P&L {money(item.get('current_pnl'))} | Duration {duration(item.get('hold_duration_seconds'))}",
                ]
            )
        )
    return "\n\n".join(sections)
