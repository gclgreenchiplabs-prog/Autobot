from __future__ import annotations

from typing import Any, Dict

from app.notifications.models import NotificationRecord, NotificationType
from app.notifications import templates


class NotificationFormatter:
    def format(self, notification: NotificationRecord) -> Dict[str, str]:
        formatter = {
            NotificationType.SIGNAL_GENERATED.value: self._format_signal,
            NotificationType.ORDER_SUBMITTED.value: self._format_order_submitted,
            NotificationType.ORDER_FILLED.value: self._format_order_filled,
            NotificationType.POSITION_HOLD.value: self._format_position_hold,
            NotificationType.POSITION_EXITED.value: self._format_position_exited,
            NotificationType.FIVE_MINUTE_STATUS.value: self._format_status,
        }.get(notification.notification_type, self._format_generic)
        return formatter(notification)

    def _format_signal(self, notification: NotificationRecord) -> Dict[str, str]:
        details = notification.payload_json
        instrument = " ".join(
            str(value) for value in [notification.symbol, notification.strike, notification.option_type] if value not in {None, ""}
        ).strip() or notification.symbol or "Signal"
        title = f"MARKET MOVE AI - SIGNAL GENERATED"
        summary = (
            f"{notification.symbol} {details.get('direction', notification.side or '')} "
            f"entry {templates.plain_money(details.get('preferred_entry', notification.entry_price))} "
            f"SL {templates.plain_money(details.get('sl', notification.initial_stop))}"
        ).strip()
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Symbol: {notification.symbol}",
                f"Instrument: {instrument}",
                f"Expiry: {templates.text(notification.expiry)}",
                f"Strategy: {templates.text(notification.strategy)}",
                f"Direction: {templates.text(details.get('direction', notification.side))}",
                f"Confidence: {templates.text(details.get('confidence'))}",
                "",
                f"Entry zone: {templates.text(details.get('entry_zone'))}",
                f"Preferred entry: {templates.plain_money(details.get('preferred_entry', notification.entry_price))}",
                f"SL: {templates.plain_money(details.get('sl', notification.initial_stop))}",
                f"T1: {templates.plain_money(notification.t1)}",
                f"T2: {templates.plain_money(notification.t2)}",
                f"T3: {templates.plain_money(notification.t3)}",
                f"Stretch target: {templates.plain_money(notification.stretch_target)}",
                f"RR: {templates.text(details.get('base_rr'))} / Stretch {templates.text(details.get('stretch_rr'))}",
                "",
                f"Lots/Qty: {templates.text(notification.lots)} lots / {templates.text(notification.quantity)} qty",
                f"Estimated capital: {templates.plain_money(details.get('estimated_capital', notification.capital_used_trade))}",
                f"Available capital before trade: {templates.plain_money(notification.capital_available)}",
                "",
                "Reason:",
                templates.text(notification.reason or details.get("reason")),
                "",
                "Invalidation:",
                templates.text(details.get("invalidation_condition")),
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_order_submitted(self, notification: NotificationRecord) -> Dict[str, str]:
        details = notification.payload_json
        title = "ORDER SUBMITTED"
        summary = f"{notification.symbol} {templates.text(notification.side)} {templates.text(notification.quantity)} via {templates.text(details.get('broker'))}"
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Trade ID: {templates.text(notification.trade_id)}",
                f"Idempotency key: {templates.text(details.get('idempotency_key'))}",
                f"Broker: {templates.text(details.get('broker'))}",
                f"Symbol: {templates.text(notification.symbol)}",
                f"Expiry: {templates.text(notification.expiry)}",
                f"Strike: {templates.text(notification.strike)}",
                f"Side: {templates.text(notification.side)}",
                f"Quantity: {templates.text(notification.quantity)}",
                f"Order type: {templates.text(details.get('order_type'))}",
                f"Requested price: {templates.plain_money(details.get('requested_price', notification.entry_price))}",
                f"Estimated capital: {templates.plain_money(notification.capital_used_trade)}",
                f"Capital before submission: {templates.plain_money(details.get('capital_before_submission'))}",
                f"Capital reserved: {templates.plain_money(notification.capital_reserved)}",
                f"Capital remaining: {templates.plain_money(notification.capital_available)}",
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_order_filled(self, notification: NotificationRecord) -> Dict[str, str]:
        details = notification.payload_json
        title = "ORDER FILLED"
        summary = f"{notification.symbol} filled at {templates.plain_money(details.get('average_fill_price', notification.entry_price))}"
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Requested price: {templates.plain_money(details.get('requested_price'))}",
                f"Average fill price: {templates.plain_money(details.get('average_fill_price', notification.entry_price))}",
                f"Filled quantity: {templates.text(details.get('filled_quantity', notification.quantity))}",
                f"Broker order ID: {templates.text(notification.broker_order_id)}",
                f"Fill timestamp: {templates.text(details.get('fill_timestamp'))}",
                f"Slippage: {templates.plain_money(details.get('slippage'))}",
                f"Charges estimate: {templates.plain_money(details.get('charges_estimate'))}",
                f"Capital actually used: {templates.plain_money(notification.capital_used_trade)}",
                f"Capital available after fill: {templates.plain_money(notification.capital_available)}",
                f"SL/T1/T2/T3: {templates.plain_money(notification.initial_stop)} / {templates.plain_money(notification.t1)} / {templates.plain_money(notification.t2)} / {templates.plain_money(notification.t3)}",
                f"Position status: {templates.text(notification.position_status)}",
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_position_hold(self, notification: NotificationRecord) -> Dict[str, str]:
        title = f"POSITION HOLD - {templates.text(notification.symbol)}"
        summary = f"{notification.symbol} open P&L {templates.money(notification.trade_pnl)} with stop {templates.plain_money(notification.current_stop)}"
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Expiry: {templates.text(notification.expiry)}",
                f"Entry: {templates.plain_money(notification.entry_price)}",
                f"Current: {templates.plain_money(notification.current_price)}",
                f"Highest: {templates.plain_money(notification.highest_price)}",
                "",
                f"T1 {templates.plain_money(notification.t1)}: {templates.text(notification.t1_status)}",
                f"T2 {templates.plain_money(notification.t2)}: {templates.text(notification.t2_status)}",
                f"T3 {templates.plain_money(notification.t3)}: {templates.text(notification.t3_status)}",
                f"Next projected target: {templates.plain_money(notification.next_predicted_target)}",
                "",
                f"SL/TSL: {templates.plain_money(notification.current_stop)}",
                f"Locked profit: {templates.money(notification.locked_profit)}",
                f"Open P&L: {templates.money(notification.trade_pnl)}",
                f"Highest profit touched: {templates.money(notification.highest_profit)}",
                "",
                "Hold reason:",
                templates.text(notification.reason or notification.payload_json.get("hold_reason")),
                "",
                "Exit condition:",
                templates.text(notification.payload_json.get("exit_condition")),
                "",
                f"Capital used: {templates.plain_money(notification.capital_used_trade)}",
                f"Day P&L: {templates.money(notification.day_total_pnl)}",
                f"Available capital: {templates.plain_money(notification.capital_available)}",
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_position_exited(self, notification: NotificationRecord) -> Dict[str, str]:
        details = notification.payload_json
        title = f"POSITION EXITED - {templates.text(notification.symbol)}"
        summary = f"{notification.symbol} net P&L {templates.money(details.get('net_pnl', notification.trade_pnl))} after release {templates.plain_money(notification.capital_released)}"
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Expiry: {templates.text(notification.expiry)}",
                f"Strategy: {templates.text(notification.strategy)}",
                "",
                "Entry:",
                f"{templates.plain_money(notification.entry_price)} at {templates.text(details.get('entry_timestamp'))}",
                "",
                "Exit:",
                f"{templates.plain_money(notification.exit_price)} at {templates.text(details.get('exit_timestamp'))}",
                "",
                "Holding time:",
                templates.duration(notification.hold_duration_seconds),
                "",
                f"T1: {templates.text(notification.t1_status)}",
                f"T2: {templates.text(notification.t2_status)}",
                f"T3: {templates.text(notification.t3_status)}",
                "",
                f"Highest price: {templates.plain_money(notification.highest_price)}",
                f"Highest profit touched: {templates.money(notification.highest_profit)}",
                f"Final TSL: {templates.plain_money(notification.current_stop)}",
                "",
                "Exit reason:",
                templates.text(notification.reason or details.get("exit_reason")),
                "",
                f"Gross P&L: {templates.money(notification.trade_pnl)}",
                f"Charges: {templates.plain_money(details.get('charges'))}",
                f"Net P&L: {templates.money(details.get('net_pnl', notification.trade_pnl))}",
                f"Net return: {templates.pct(details.get('net_pnl_pct', notification.trade_pnl_pct))}",
                "",
                f"Capital used: {templates.plain_money(notification.capital_used_trade)}",
                f"Capital released: {templates.plain_money(notification.capital_released)}",
                "",
                f"Day realized P&L: {templates.money(notification.day_realized_pnl)}",
                f"Day unrealized P&L: {templates.money(notification.day_unrealized_pnl)}",
                f"Total day P&L: {templates.money(notification.day_total_pnl)}",
                f"Available capital: {templates.plain_money(notification.capital_available)}",
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_status(self, notification: NotificationRecord) -> Dict[str, str]:
        details = notification.payload_json
        account = details.get("account", {})
        positions = details.get("open_positions", [])
        recent_closed = details.get("recently_closed_positions", [])
        events = details.get("recent_events", [])
        title = "FIVE MINUTE STATUS"
        summary = (
            f"Bot {templates.text(details.get('system', {}).get('bot_state'))} | "
            f"Open trades {templates.text(account.get('open_trades'))} | "
            f"Day P&L {templates.money(account.get('total_day_pnl'))}"
        )
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                "SYSTEM",
                f"Bot state: {templates.text(details.get('system', {}).get('bot_state'))}",
                f"Session state: {templates.text(details.get('system', {}).get('session_state'))}",
                f"Current IST time: {templates.text(details.get('system', {}).get('current_ist_time'))}",
                f"Execution mode: {templates.text(details.get('system', {}).get('execution_mode'))}",
                f"Data state: {templates.text(details.get('system', {}).get('data_state'))}",
                f"Primary/Active/Standby broker: {templates.text(details.get('system', {}).get('primary_broker'))} / {templates.text(details.get('system', {}).get('active_broker'))} / {templates.text(details.get('system', {}).get('standby_broker'))}",
                f"Health status: {templates.text(details.get('system', {}).get('health_status'))}",
                "",
                "ACCOUNT",
                f"Opening capital: {templates.plain_money(account.get('opening_capital'))}",
                f"Account equity: {templates.plain_money(account.get('account_equity'))}",
                f"Capital used: {templates.plain_money(account.get('capital_used_day'))}",
                f"Capital reserved: {templates.plain_money(account.get('capital_reserved'))}",
                f"Capital available: {templates.plain_money(account.get('capital_available'))}",
                f"Day realized P&L: {templates.money(account.get('realized_pnl'))}",
                f"Day unrealized P&L: {templates.money(account.get('unrealized_pnl'))}",
                f"Total day P&L: {templates.money(account.get('total_day_pnl'))}",
                f"Wins/Losses: {templates.text(account.get('wins'))} / {templates.text(account.get('losses'))}",
                f"Open/Closed trades: {templates.text(account.get('open_trades'))} / {templates.text(account.get('closed_trades'))}",
                "",
                "OPEN POSITIONS",
                templates.render_status_list(positions),
                "",
                "RECENTLY CLOSED POSITIONS",
                "None" if not recent_closed else "\n\n".join(
                    f"{templates.text(item.get('symbol'))} | Exit {templates.plain_money(item.get('exit_price'))} | Net P&L {templates.money(item.get('total_pnl'))}"
                    for item in recent_closed
                ),
                "",
                "RECENT EVENTS",
                "None" if not events else "\n".join(
                    f"{templates.text(item.get('event_type'))} | {templates.text(item.get('symbol'))} | {templates.text(item.get('severity'))} | {templates.text(item.get('reason'))}"
                    for item in events
                ),
            ]
        )
        return {"title": title, "summary": summary, "body": body}

    def _format_generic(self, notification: NotificationRecord) -> Dict[str, str]:
        title = notification.title or notification.notification_type.replace("_", " ")
        summary = notification.summary or notification.reason or notification.notification_type
        body = templates.join_lines(
            [
                templates.html_header(title),
                "",
                f"Type: {notification.notification_type}",
                f"Severity: {notification.severity}",
                f"Summary: {summary}",
                f"Reason: {templates.text(notification.reason)}",
            ]
        )
        return {"title": title, "summary": summary, "body": body}
