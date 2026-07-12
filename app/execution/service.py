from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.brokers.readiness import BrokerReadinessService
from app.brokers.router import BrokerRouter
from app.database.repository import Repository
from app.event_bus import EventBus
from app.execution.charges import BrokerChargesCalculator
from app.models import OrderRequest
from app.notifications.models import NotificationType
from app.scheduler.session_scheduler import SessionScheduler
from app.settings import Settings
from app.state_store import StateStore
from app.telemetry import TelemetryService


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _side_multiplier(side: str) -> int:
    normalized = str(side or "BUY").strip().upper()
    return -1 if normalized in {"SELL", "SHORT"} else 1


class ExecutionService:
    def __init__(
        self,
        *,
        settings: Settings,
        state_store: StateStore,
        repository: Repository,
        event_bus: EventBus,
        broker_router: BrokerRouter,
        telemetry_service: TelemetryService,
        scheduler: SessionScheduler,
        broker_readiness_service: BrokerReadinessService,
        market_data_service: Any,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.repository = repository
        self.event_bus = event_bus
        self.broker_router = broker_router
        self.telemetry_service = telemetry_service
        self.scheduler = scheduler
        self.broker_readiness_service = broker_readiness_service
        self.market_data_service = market_data_service
        self.charges = BrokerChargesCalculator(settings)

    def status(self) -> Dict[str, Any]:
        account = self.telemetry_service.build_account_snapshot(reason="execution-status").to_dict()
        return {
            "execution_mode": account["execution_mode"],
            "active_execution_broker": account["active_execution_broker"],
            "configured_primary_broker": account["configured_primary_broker"],
            "standby_broker": account["standby_broker"],
            "market_data_mode": self.settings.market_data_mode.lower(),
            "capital_available": account["capital_available"],
            "capital_used_day": account["capital_used_day"],
            "capital_reserved": account["capital_reserved"],
            "open_positions": account["open_trades"],
            "closed_trades": account["closed_trades"],
            "live_order_enable": self.settings.live_order_enable,
            "explicit_live_confirmation": self.settings.explicit_live_confirmation,
            "execution_failover_enabled": self.settings.enable_execution_failover,
            "execution_failover_approved": self.settings.execution_failover_approved,
        }

    def place_order(self, order: OrderRequest, *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        self._assert_execution_allowed()
        fill_price = self._resolve_price(order)
        capital_before = self.telemetry_service.build_account_snapshot(reason="execution-place").capital_available
        capital_required = round(fill_price * order.quantity, 2)
        if capital_required > capital_before:
            return self._blocked_order(order, "Insufficient available capital.", notification_type=NotificationType.RISK_BLOCKED.value)

        trade_id = f"trade-{uuid4().hex[:12]}"
        order_id = f"order-{uuid4().hex[:12]}"
        broker_order_id = f"{self._active_broker()}-{uuid4().hex[:10]}"
        submitted_at = datetime.now(timezone.utc).isoformat()
        broker_result = self.broker_router.place_order(order, idempotency_key=idempotency_key)
        entry_charges = self.charges.calculate(price=fill_price, quantity=order.quantity, side=order.action)

        order_record = {
            "order_id": order_id,
            "trade_id": trade_id,
            "broker_order_id": broker_order_id,
            "broker": broker_result["broker"],
            "symbol": order.symbol,
            "quantity": order.quantity,
            "action": order.action.upper(),
            "requested_price": order.price,
            "fill_price": fill_price,
            "status": "FILLED" if self.settings.is_paper_mode else str(broker_result.get("status", "SUBMITTED")).upper(),
            "mode": broker_result["mode"],
            "capital_before": round(capital_before, 2),
            "capital_required": capital_required,
            "charges": entry_charges.to_dict(),
            "submitted_at": submitted_at,
            "payload_json": broker_result,
        }
        self._append_state_record("orders", order_record)
        self.repository.save_order(order_record)
        self.event_bus.publish(
            {
                "event_type": NotificationType.ORDER_SUBMITTED.value,
                "source": "execution",
                "severity": "INFO",
                "symbol": order.symbol,
                "title": f"Order submitted {order.symbol}",
                "description": f"{order.quantity} {order.action.upper()} @ {fill_price:.2f}",
                "reason": "Execution request accepted.",
                "order_id": order_id,
                "trade_id": trade_id,
                "payload": order_record,
            }
        )

        if self.settings.is_paper_mode:
            position_record = {
                "trade_id": trade_id,
                "order_id": order_id,
                "broker_order_id": broker_order_id,
                "symbol": order.symbol,
                "quantity": order.quantity,
                "lots": 1,
                "side": order.action.upper(),
                "entry_price": fill_price,
                "current_price": fill_price,
                "capital_used_trade": capital_required,
                "entry_charges": entry_charges.to_dict(),
                "entry_charges_total": entry_charges.total,
                "entry_timestamp": submitted_at,
                "position_status": "OPEN",
            }
            self._append_state_record("positions", position_record)
            self.repository.save_position(position_record)
            self.event_bus.publish(
                {
                    "event_type": NotificationType.ORDER_FILLED.value,
                    "source": "execution",
                    "severity": "INFO",
                    "symbol": order.symbol,
                    "title": f"Order filled {order.symbol}",
                    "description": f"{order.quantity} {order.action.upper()} filled @ {fill_price:.2f}",
                    "reason": "Paper execution fills immediately.",
                    "order_id": order_id,
                    "trade_id": trade_id,
                    "payload": {
                        **order_record,
                        "charges_estimate": entry_charges.total,
                    },
                }
            )
            self.event_bus.publish(
                {
                    "event_type": NotificationType.POSITION_OPENED.value,
                    "source": "execution",
                    "severity": "INFO",
                    "symbol": order.symbol,
                    "title": f"Position opened {order.symbol}",
                    "description": f"Capital used {capital_required:.2f}",
                    "reason": "Paper fill converted order to open position.",
                    "trade_id": trade_id,
                    "payload": position_record,
                }
            )
        else:
            self._reserve_capital(capital_required)

        return {
            **order_record,
            "account_after": self.telemetry_service.build_account_snapshot(reason="execution-place-result").to_dict(),
        }

    def exit_position(self, trade_id: str, *, exit_price: Optional[float] = None, reason: str = "manual exit") -> Dict[str, Any]:
        positions = [dict(item) for item in self.state_store.get("positions", [])]
        target = next((item for item in positions if item.get("trade_id") == trade_id), None)
        if target is None:
            raise ValueError("position not found")

        if exit_price is not None:
            fill_price = round(_as_float(exit_price), 2)
        else:
            fill_price = self._resolve_price(
                OrderRequest(symbol=target["symbol"], quantity=int(target["quantity"]), action="SELL")
            )
        quantity = int(target["quantity"])
        side = str(target.get("side") or "BUY").upper()
        capital_used_trade = round(_as_float(target.get("capital_used_trade")), 2)
        gross_pnl = round((fill_price - _as_float(target.get("entry_price"))) * quantity * _side_multiplier(side), 2)
        exit_side = "SELL" if side in {"BUY", "LONG"} else "BUY"
        exit_charges = self.charges.calculate(price=fill_price, quantity=quantity, side=exit_side)
        entry_charges_total = _as_float(target.get("entry_charges_total") or (target.get("entry_charges") or {}).get("total"))
        total_charges = round(entry_charges_total + exit_charges.total, 2)
        net_pnl = round(gross_pnl - total_charges, 2)
        capital_released = round((fill_price * quantity) - exit_charges.total, 2)
        exit_timestamp = datetime.now(timezone.utc).isoformat()

        closed_trade = {
            **target,
            "exit_price": fill_price,
            "exit_timestamp": exit_timestamp,
            "exit_reason": reason,
            "gross_pnl": gross_pnl,
            "trade_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "charges_total": total_charges,
            "exit_charges": exit_charges.to_dict(),
            "capital_released": capital_released,
            "status": "CLOSED",
            "position_status": "CLOSED",
        }
        self.state_store.set("positions", [item for item in positions if item.get("trade_id") != trade_id])
        self._append_state_record("closed_trades", closed_trade)
        self.event_bus.publish(
            {
                "event_type": NotificationType.POSITION_EXITED.value,
                "source": "execution",
                "severity": "INFO",
                "symbol": target["symbol"],
                "title": f"Position exited {target['symbol']}",
                "description": f"Net P&L {net_pnl:.2f}",
                "reason": reason,
                "trade_id": trade_id,
                "payload": closed_trade,
            }
        )
        return {
            **closed_trade,
            "account_after": self.telemetry_service.build_account_snapshot(reason="execution-exit-result").to_dict(),
        }

    def _blocked_order(self, order: OrderRequest, reason: str, *, notification_type: str) -> Dict[str, Any]:
        payload = {
            "status": "BLOCKED",
            "symbol": order.symbol,
            "quantity": order.quantity,
            "action": order.action.upper(),
            "reason": reason,
            "mode": "paper" if self.settings.is_paper_mode else "live",
        }
        self.event_bus.publish(
            {
                "event_type": notification_type,
                "source": "execution",
                "severity": "WARNING",
                "symbol": order.symbol,
                "title": f"Execution blocked {order.symbol}",
                "description": reason,
                "reason": reason,
                "payload": payload,
            }
        )
        return payload

    def _assert_execution_allowed(self) -> None:
        lifecycle = self.state_store.get("lifecycle") or {}
        if lifecycle.get("kill_switch"):
            raise ValueError("kill switch is active")
        if lifecycle.get("status") in {"paused", "stopped"}:
            raise ValueError(f"lifecycle status blocks execution: {lifecycle.get('status')}")
        session_state = str(self.scheduler.get_state().get("session_state") or "")
        if session_state in {"CLOSED", "NOT_READY"} and not self.settings.forced_test_mode:
            raise ValueError("session does not allow orders")
        if not self.settings.is_paper_mode:
            broker = self._active_broker()
            readiness = self.broker_readiness_service.snapshots().get(broker) or {}
            if not readiness.get("execution_ready"):
                raise ValueError(str((readiness.get("capabilities") or {}).get("execution", {}).get("reason") or readiness.get("reason") or "execution not ready"))

    def _resolve_price(self, order: OrderRequest) -> float:
        if order.price is not None:
            return round(float(order.price), 2)
        quote = self._find_quote(order.symbol)
        if quote and quote.get("ltp") is not None:
            return round(float(quote["ltp"]), 2)
        raise ValueError("price is required when no latest quote is available")

    def _find_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        for quote in self.market_data_service.quotes():
            if str(quote.get("symbol") or "").upper() == str(symbol).upper():
                return quote
        return None

    def _active_broker(self) -> str:
        return "paper" if self.settings.is_paper_mode else self.settings.execution_broker

    def _append_state_record(self, key: str, payload: Dict[str, Any]) -> None:
        records = [dict(item) for item in self.state_store.get(key, [])]
        records.append(payload)
        self.state_store.set(key, records)

    def _reserve_capital(self, amount: float) -> None:
        account = dict(self.state_store.get("account") or {"opening_capital": self.settings.opening_capital, "capital_reserved": 0.0})
        account["opening_capital"] = _as_float(account.get("opening_capital"), self.settings.opening_capital)
        account["capital_reserved"] = round(_as_float(account.get("capital_reserved")) + amount, 2)
        self.state_store.set("account", account)
