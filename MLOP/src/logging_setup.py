"""Logger factory used by run.py and any helpers."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logger(log_file: Path, level: int = logging.INFO) -> logging.Logger:
    """Configure the root `mlops` logger to write to both stderr and log_file.

    Logs go to stderr so stdout stays clean for the final JSON payload,
    which keeps docker logs parseable.
    """
    logger = logging.getLogger("mlops")
    logger.setLevel(level)
    # remove any pre-existing handlers so reruns inside the same process do not double-log
    for h in list(logger.handlers):
        logger.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger
