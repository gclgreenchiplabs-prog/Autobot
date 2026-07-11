import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: str | None = None, log_level: str = "INFO", max_bytes: int = 5_242_880, backup_count: int = 5) -> Logger:
    logger = logging.getLogger("market_move_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        for file_name in ["app.log", "api.log", "broker.log", "database.log", "health.log", "tasks.log"]:
            file_handler = RotatingFileHandler(log_path / file_name, maxBytes=max_bytes, backupCount=backup_count)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
