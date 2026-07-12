import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from app.settings import Settings, SettingsValidationError, load_settings, validate_settings


def test_settings_defaults_to_paper_mode_and_fyers_primary():
    settings = load_settings(env_path=None)

    assert settings.primary_broker == "fyers"
    assert settings.standby_broker == "dhan"
    assert settings.trading_mode == "paper"
    assert settings.is_paper_mode is True


def test_settings_reads_values_from_env_file(tmp_path: Path):
    env_file = tmp_path / "config.env"
    env_file.write_text(
        "PRIMARY_BROKER=dhan\n"
        "STANDBY_BROKER=fyers\n"
        "TRADING_MODE=live\n",
        encoding="utf-8",
    )

    settings = load_settings(env_path=env_file)

    assert settings.primary_broker == "dhan"
    assert settings.standby_broker == "fyers"
    assert settings.trading_mode == "live"
    assert settings.is_paper_mode is False


def test_settings_supports_execution_mode_and_broker_specific_aliases(tmp_path: Path):
    env_file = tmp_path / "aliases.env"
    env_file.write_text(
        "EXECUTION_MODE=PAPER\n"
        "EXECUTION_BROKER=FYERS\n"
        "OPTION_CHAIN_BROKER=DHAN\n"
        "FYERS_CLIENT_ID=fyers-id\n"
        "FYERS_SECRET_KEY=fyers-secret\n"
        "FYERS_ACCESS_TOKEN=fyers-token\n"
        "DHAN_CLIENT_ID=dhan-id\n"
        "DHAN_ACCESS_TOKEN=dhan-token\n"
        "LIVE_ORDER_ENABLE=false\n"
        "LIVE_MARKET_DATA_ENABLE=false\n"
        "EXECUTION_FAILOVER_APPROVED=true\n"
        "BROKERAGE_FLAT_PER_ORDER=20\n"
        "GST_PCT=18\n"
        "PRIMARY_MARKET_DATA_BROKER=FYERS\n"
        "STANDBY_MARKET_DATA_BROKER=DHAN\n",
        encoding="utf-8",
    )

    settings = load_settings(env_path=env_file)

    assert settings.trading_mode == "paper"
    assert settings.execution_broker == "fyers"
    assert settings.option_chain_broker == "dhan"
    assert settings.fyers_client_id == "fyers-id"
    assert settings.api_key == "fyers-id"
    assert settings.fyers_secret_key == "fyers-secret"
    assert settings.api_secret == "fyers-secret"
    assert settings.fyers_access_token == "fyers-token"
    assert settings.access_token == "fyers-token"
    assert settings.dhan_client_id == "dhan-id"
    assert settings.dhan_access_token == "dhan-token"
    assert settings.execution_failover_approved is True
    assert settings.brokerage_flat_per_order == 20.0
    assert settings.gst_pct == 18.0


def test_settings_validate_rejects_invalid_execution_mode():
    with pytest.raises(SettingsValidationError):
        validate_settings(Settings(trading_mode="invalid"))


def test_settings_validate_rejects_negative_charge_configuration():
    with pytest.raises(SettingsValidationError):
        validate_settings(Settings(brokerage_flat_per_order=-1.0))
