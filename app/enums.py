from enum import Enum


class BrokerName(str, Enum):
    FYERS = "fyers"
    DHAN = "dhan"
    PAPER = "paper"


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"
