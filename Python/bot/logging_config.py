"""Logger factory for the Binance Futures Testnet bot."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logger(log_file: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure the root binance_bot logger with both stdout and file handlers."""
    logger = logging.getLogger("binance_bot")
    logger.setLevel(level)
    for h in list(logger.handlers):
        logger.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger
