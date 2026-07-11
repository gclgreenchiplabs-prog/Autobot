import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.settings import Settings, load_settings


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
