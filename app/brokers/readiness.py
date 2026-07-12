from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.event_bus import EventBus
from app.settings import Settings
from app.state_store import StateStore


BROKER_STATES = {
    "NOT_CONFIGURED",
    "CONFIGURED",
    "DISABLED",
    "CREDENTIALS_MISSING",
    "SDK_NOT_INSTALLED",
    "AUTHENTICATION_REQUIRED",
    "AUTHENTICATING",
    "AUTHENTICATED",
    "CONNECTING",
    "CONNECTED",
    "DEGRADED",
    "READY",
    "FAILED",
}


@dataclass
class BrokerCapabilityReadiness:
    broker: str
    capability: str
    configured: bool
    enabled: bool
    credentials_present: bool
    sdk_available: bool
    authenticated: bool
    connected: bool
    market_data_ready: bool
    option_chain_ready: bool
    execution_ready: bool
    active: bool
    status: str
    reason: str
    last_error: Optional[str] = None
    last_checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrokerCapabilityEvaluator:
    def __init__(
        self,
        *,
        settings: Settings,
        broker: str,
        sdk_available: bool,
        authenticated: bool,
        connected: bool,
        market_data_state: Optional[Dict[str, Any]] = None,
        market_data_capability_state: Optional[Dict[str, Any]] = None,
        execution_connection_ready: bool = False,
        option_chain_connection_ready: bool = False,
        last_error: Optional[str] = None,
    ) -> None:
        self.settings = settings
        self.broker = broker.lower()
        self.sdk_available = sdk_available
        self.authenticated = authenticated
        self.connected = connected
        self.market_data_state = market_data_state or {}
        self.market_data_capability_state = market_data_capability_state or {}
        self.execution_connection_ready = execution_connection_ready
        self.option_chain_connection_ready = option_chain_connection_ready
        self.last_error = last_error
        self._checked_at = _now_iso()

    @property
    def configured(self) -> bool:
        if self.broker == "fyers":
            return self.settings.fyers_configured
        return self.settings.dhan_configured

    @property
    def credentials_present(self) -> bool:
        if self.broker == "fyers":
            return bool(self.settings.fyers_client_id and self.settings.fyers_secret_key and self.settings.fyers_access_token)
        return bool(self.settings.dhan_client_id and self.settings.dhan_access_token)

    @property
    def overall_enabled(self) -> bool:
        return bool(self._market_data_enabled_flag() or self._execution_enabled_flag() or self._option_chain_enabled_flag())

    @property
    def active(self) -> bool:
        return self.market_data_active or self.execution_active

    @property
    def market_data_active(self) -> bool:
        return self.settings.market_data_mode == "LIVE" and self.market_data_state.get("active_market_data_source") == self.broker

    @property
    def execution_active(self) -> bool:
        return self.settings.trading_mode == "live" and self.settings.execution_broker == self.broker

    def configuration_readiness(self) -> BrokerCapabilityReadiness:
        if not self.configured:
            return self._record(
                capability="configuration",
                enabled=self.overall_enabled,
                status="NOT_CONFIGURED",
                reason="Configured flag is false.",
            )
        reason = "Broker configured in environment."
        if self.settings.is_paper_mode and self.settings.market_data_mode == "FIXTURE":
            reason = "Configured but inactive because execution mode is PAPER and market-data mode is FIXTURE."
        return self._record(
            capability="configuration",
            enabled=self.overall_enabled,
            status="CONFIGURED",
            reason=reason,
        )

    def authentication_readiness(self) -> BrokerCapabilityReadiness:
        if not self.configured:
            return self._record("authentication", False, "NOT_CONFIGURED", "Configured flag is false.")
        if not self.credentials_present:
            return self._record("authentication", self.overall_enabled, "CREDENTIALS_MISSING", "Broker credentials are incomplete.")
        if not self.sdk_available:
            return self._record("authentication", self.overall_enabled, "SDK_NOT_INSTALLED", "Required SDK is not installed.")
        if self.settings.is_paper_mode and self.settings.market_data_mode == "FIXTURE":
            return self._record("authentication", self.overall_enabled, "CONFIGURED", "Authentication is not required while the broker remains inactive.")
        if not self.overall_enabled:
            return self._record("authentication", False, "DISABLED", "Live broker capabilities are disabled.")
        if self.authenticated:
            return self._record("authentication", True, "AUTHENTICATED", "Authentication is established.")
        return self._record("authentication", True, "AUTHENTICATION_REQUIRED", "Authentication has not been performed.")

    def market_data_readiness(self) -> BrokerCapabilityReadiness:
        enabled = self._market_data_enabled_flag()
        if not self.configured:
            return self._record("market_data", enabled, "NOT_CONFIGURED", "Configured flag is false.")
        if self.settings.market_data_mode != "LIVE":
            return self._record("market_data", False, "DISABLED", f"Market-data mode is {self.settings.market_data_mode}, so live broker data is inactive.")
        if not self.settings.live_market_data_enable:
            return self._record("market_data", False, "DISABLED", "LIVE_MARKET_DATA_ENABLE is false.")
        if not enabled:
            return self._record("market_data", False, "DISABLED", "Broker market-data capability is disabled.")
        if not self.credentials_present:
            return self._record("market_data", True, "CREDENTIALS_MISSING", "Market-data credentials are incomplete.")
        if not self.sdk_available:
            return self._record("market_data", True, "SDK_NOT_INSTALLED", "Required market-data SDK is not installed.")
        if not self.authenticated:
            return self._record("market_data", True, "AUTHENTICATION_REQUIRED", "Broker authentication is required before live market data can start.")

        adapter_state = str(self.market_data_capability_state.get("state") or "AUTHENTICATION_REQUIRED")
        adapter_reason = str(self.market_data_capability_state.get("reason") or "Market-data connection is not active.")
        ready = bool(self.market_data_capability_state.get("market_data_ready"))
        connected = bool(self.market_data_capability_state.get("connected"))
        if ready:
            return self._record("market_data", True, "READY", adapter_reason, connected=True, market_data_ready=True, active=self.market_data_active)
        if connected:
            return self._record("market_data", True, "CONNECTED", adapter_reason, connected=True, active=self.market_data_active)
        if adapter_state in BROKER_STATES:
            return self._record("market_data", True, adapter_state, adapter_reason, active=self.market_data_active)
        return self._record("market_data", True, "DEGRADED", adapter_reason, active=self.market_data_active)

    def option_chain_readiness(self) -> BrokerCapabilityReadiness:
        enabled = self._option_chain_enabled_flag()
        if self.broker != "dhan":
            return self._record("option_chain", False, "DISABLED", "Option-chain support is not enabled for this broker.")
        if not self.configured:
            return self._record("option_chain", enabled, "NOT_CONFIGURED", "Configured flag is false.")
        if not enabled:
            return self._record("option_chain", False, "DISABLED", "Dhan option-chain capability is disabled.")
        if not self.credentials_present:
            return self._record("option_chain", True, "CREDENTIALS_MISSING", "Dhan credentials are incomplete.")
        if not self.authenticated:
            return self._record("option_chain", True, "AUTHENTICATION_REQUIRED", "Dhan authentication is required before option-chain use.")
        if not self.option_chain_connection_ready:
            return self._record("option_chain", True, "DEGRADED", "Option-chain runtime is not implemented in this patch.")
        return self._record("option_chain", True, "READY", "Option-chain readiness checks passed.", option_chain_ready=True, active=self.active)

    def execution_readiness(self) -> BrokerCapabilityReadiness:
        enabled = self._execution_enabled_flag()
        if not self.configured:
            return self._record("execution", enabled, "NOT_CONFIGURED", "Configured flag is false.")
        if self.settings.trading_mode != "live":
            return self._record("execution", False, "DISABLED", "Execution mode is PAPER.")
        if not self.settings.live_order_enable:
            return self._record("execution", False, "DISABLED", "LIVE_ORDER_ENABLE is false.")
        if not self.settings.explicit_live_confirmation:
            return self._record("execution", False, "DISABLED", "EXPLICIT_LIVE_CONFIRMATION is false.")
        if not enabled:
            return self._record("execution", False, "DISABLED", "Broker execution capability is disabled.")
        if self.execution_active and self.broker != self.settings.primary_broker:
            if not self.settings.enable_execution_failover:
                return self._record("execution", True, "DISABLED", "ENABLE_EXECUTION_FAILOVER is false.")
            if self.settings.failover_requires_manual_approval and not self.settings.execution_failover_approved:
                return self._record("execution", True, "DISABLED", "EXECUTION_FAILOVER_APPROVED is false.")
        if self.broker == "dhan" and not self.settings.dhan_order_api_enable:
            return self._record("execution", True, "DISABLED", "DHAN_ORDER_API_ENABLE is false.")
        if self.broker == "dhan" and not self.settings.dhan_static_ip_ready:
            return self._record("execution", True, "DISABLED", "DHAN_STATIC_IP_READY is false.")
        if not self.credentials_present:
            return self._record("execution", True, "CREDENTIALS_MISSING", "Execution credentials are incomplete.")
        if not self.sdk_available:
            return self._record("execution", True, "SDK_NOT_INSTALLED", "Required execution SDK is not installed.")
        if not self.authenticated:
            return self._record("execution", True, "AUTHENTICATION_REQUIRED", "Broker authentication is required before live execution.")
        if not bool(self.market_data_capability_state.get("market_data_ready")):
            return self._record("execution", True, "DEGRADED", "Live market data is not ready, so execution remains blocked.", active=self.execution_active)
        if not self.execution_connection_ready:
            return self._record("execution", True, "DEGRADED", "Execution connection readiness is not implemented in this patch.", active=self.execution_active)
        return self._record("execution", True, "READY", "Execution readiness checks passed.", execution_ready=True, active=self.execution_active)

    def health_snapshot(self) -> Dict[str, Any]:
        configuration = self.configuration_readiness()
        authentication = self.authentication_readiness()
        market_data = self.market_data_readiness()
        option_chain = self.option_chain_readiness()
        execution = self.execution_readiness()
        if not self.configured:
            status = "NOT_CONFIGURED"
            reason = configuration.reason
        elif market_data.status == "READY" or execution.status == "READY" or option_chain.status == "READY":
            status = "READY"
            reason = "At least one live capability is ready."
        elif market_data.status == "CONNECTED":
            status = "CONNECTED"
            reason = market_data.reason
        elif authentication.status == "AUTHENTICATED":
            status = "AUTHENTICATED"
            reason = authentication.reason
        elif self.settings.is_paper_mode and self.settings.market_data_mode == "FIXTURE":
            status = "CONFIGURED"
            if self.broker == "fyers":
                reason = "Configured but inactive because execution mode is PAPER and market-data mode is FIXTURE."
            else:
                reason = "Configured standby broker; live capabilities are disabled."
        elif not self.overall_enabled:
            status = "CONFIGURED"
            reason = "Broker is configured but all live capabilities are disabled."
        else:
            status = configuration.status
            reason = configuration.reason
        return {
            "broker": self.broker,
            "configured": self.configured,
            "enabled": self.overall_enabled,
            "credentials_present": self.credentials_present,
            "sdk_available": self.sdk_available,
            "authenticated": authentication.status in {"AUTHENTICATED", "READY"},
            "connected": market_data.connected or self.execution_connection_ready,
            "market_data_ready": market_data.market_data_ready,
            "option_chain_ready": option_chain.option_chain_ready,
            "execution_ready": execution.execution_ready,
            "active": self.active,
            "status": status,
            "reason": reason,
            "last_error": self.last_error,
            "last_checked_at": self._checked_at,
            "static_ip_ready": self.settings.dhan_static_ip_ready if self.broker == "dhan" else None,
            "order_api_enabled": self.settings.dhan_order_api_enable if self.broker == "dhan" else None,
            "capabilities": {
                "configuration": configuration.to_dict(),
                "authentication": authentication.to_dict(),
                "market_data": market_data.to_dict(),
                "option_chain": option_chain.to_dict(),
                "execution": execution.to_dict(),
            },
        }

    def _market_data_enabled_flag(self) -> bool:
        return self.settings.fyers_market_data_enable if self.broker == "fyers" else self.settings.dhan_market_data_enable

    def _execution_enabled_flag(self) -> bool:
        return self.settings.fyers_execution_enable if self.broker == "fyers" else self.settings.dhan_execution_enable

    def _option_chain_enabled_flag(self) -> bool:
        return self.broker == "dhan" and self.settings.dhan_option_chain_enable

    def _record(
        self,
        capability: str,
        enabled: bool,
        status: str,
        reason: str,
        *,
        connected: Optional[bool] = None,
        market_data_ready: bool = False,
        option_chain_ready: bool = False,
        execution_ready: bool = False,
        active: Optional[bool] = None,
    ) -> BrokerCapabilityReadiness:
        return BrokerCapabilityReadiness(
            broker=self.broker,
            capability=capability,
            configured=self.configured,
            enabled=enabled,
            credentials_present=self.credentials_present,
            sdk_available=self.sdk_available,
            authenticated=self.authenticated,
            connected=self.connected if connected is None else connected,
            market_data_ready=market_data_ready,
            option_chain_ready=option_chain_ready,
            execution_ready=execution_ready,
            active=self.active if active is None else active,
            status=status,
            reason=reason,
            last_error=self.last_error,
            last_checked_at=self._checked_at,
        )


class BrokerReadinessService:
    def __init__(
        self,
        *,
        settings: Settings,
        state_store: StateStore,
        event_bus: EventBus,
        broker_router: Any,
        market_data_service: Any,
    ) -> None:
        self.settings = settings
        self.state_store = state_store
        self.event_bus = event_bus
        self.broker_router = broker_router
        self.market_data_service = market_data_service

    def refresh(self) -> Dict[str, Dict[str, Any]]:
        snapshots = self.snapshots()
        previous = self.state_store.get("broker_readiness") or {}
        previous_modes = self.state_store.get("broker_modes") or {}
        current_modes = {
            "execution_mode": self.settings.trading_mode,
            "market_data_mode": self.settings.market_data_mode,
            "execution_broker": self.settings.execution_broker,
            "primary_market_data_broker": self.settings.primary_market_data_broker,
        }
        for broker, snapshot in snapshots.items():
            old_status = ((previous.get(broker) or {}).get("status"))
            new_status = snapshot["status"]
            if old_status != new_status:
                self._publish_transition(broker, old_status, snapshot)
            if previous_modes != current_modes:
                self.event_bus.publish(
                    {
                        "event_type": "BROKER_MODE_CHANGED",
                        "source": "broker-readiness",
                        "severity": "INFO",
                        "title": f"{broker.upper()} broker mode changed",
                        "description": f"Execution mode={self.settings.trading_mode}, market-data mode={self.settings.market_data_mode}",
                        "reason": "Broker mode configuration changed.",
                        "symbol": broker.upper(),
                    }
                )
        self.state_store.set("broker_readiness", snapshots)
        self.state_store.set("broker_modes", current_modes)
        return snapshots

    def snapshots(self) -> Dict[str, Dict[str, Any]]:
        market_status = self.market_data_service.status()
        market_readiness = self.market_data_service.adapter_readiness()
        return {
            "fyers": BrokerCapabilityEvaluator(
                settings=self.settings,
                broker="fyers",
                sdk_available=bool((market_readiness.get("fyers") or {}).get("sdk_available", True)),
                authenticated=False,
                connected=bool((market_readiness.get("fyers") or {}).get("connected", False)),
                market_data_state=market_status,
                market_data_capability_state=market_readiness.get("fyers") or {},
            ).health_snapshot(),
            "dhan": BrokerCapabilityEvaluator(
                settings=self.settings,
                broker="dhan",
                sdk_available=True,
                authenticated=False,
                connected=bool((market_readiness.get("dhan") or {}).get("connected", False)),
                market_data_state=market_status,
                market_data_capability_state=market_readiness.get("dhan") or {},
            ).health_snapshot(),
        }

    def _publish_transition(self, broker: str, old_status: Optional[str], snapshot: Dict[str, Any]) -> None:
        event_type = {
            "NOT_CONFIGURED": "BROKER_NOT_READY",
            "CONFIGURED": "BROKER_CONFIGURED",
            "DISABLED": "BROKER_DISABLED",
            "CREDENTIALS_MISSING": "BROKER_CREDENTIALS_MISSING",
            "SDK_NOT_INSTALLED": "BROKER_SDK_MISSING",
            "AUTHENTICATED": "BROKER_AUTHENTICATED",
            "CONNECTED": "BROKER_CONNECTED",
            "READY": "BROKER_READY",
        }.get(snapshot["status"], "BROKER_NOT_READY")
        self.event_bus.publish(
            {
                "event_type": event_type,
                "source": "broker-readiness",
                "severity": "INFO" if snapshot["status"] in {"CONFIGURED", "AUTHENTICATED", "CONNECTED", "READY"} else "WARNING",
                "title": f"{broker.upper()} {snapshot['status'].replace('_', ' ').title()}",
                "description": snapshot["reason"],
                "reason": snapshot["reason"],
                "symbol": broker.upper(),
                "payload": {"previous_status": old_status, "current": snapshot},
            }
        )
