from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    primary_broker: str = "fyers"
    standby_broker: str = "dhan"
    trading_mode: str = "paper"
    api_key: str = ""
    api_secret: str = ""
    access_token: str = ""
    broker_pin: str = ""

    @property
    def is_paper_mode(self) -> bool:
        return self.trading_mode.lower() == "paper"


def load_settings(env_path: Optional[os.PathLike[str] | str | Path] = None) -> Settings:
    env_file = Path(env_path) if env_path is not None else None
    values = dotenv_values(env_file) if env_file else {}

    if env_file is not None and not env_file.exists():
        values = {}

    merged = {**os.environ, **values}

    return Settings(
        primary_broker=(merged.get("PRIMARY_BROKER") or "fyers").strip().lower(),
        standby_broker=(merged.get("STANDBY_BROKER") or "dhan").strip().lower(),
        trading_mode=(merged.get("TRADING_MODE") or "paper").strip().lower(),
        api_key=(merged.get("BROKER_API_KEY") or "").strip(),
        api_secret=(merged.get("BROKER_SECRET_KEY") or "").strip(),
        access_token=(merged.get("BROKER_ACCESS_TOKEN") or "").strip(),
        broker_pin=(merged.get("BROKER_PIN") or "").strip(),
    )
