"""MLOps Task 0 entry point: load config, read OHLCV CSV, write metrics + log."""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.config import ConfigError, load_config
from src.logging_setup import setup_logger
from src.metrics import write_error, write_success
from src.pipeline import DataError, compute_signal, load_data

DEFAULT_VERSION = "v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MLOps Task 0 batch job")
    p.add_argument("--input", required=True, type=Path, help="path to OHLCV CSV")
    p.add_argument("--config", required=True, type=Path, help="path to YAML config")
    p.add_argument("--output", required=True, type=Path, help="path to write metrics.json")
    p.add_argument("--log-file", required=True, type=Path, help="path to write run.log")
    return p.parse_args(argv)


def _emit(payload: dict) -> None:
    """Echo the final metrics JSON to stdout so Docker logs surface it."""
    print(json.dumps(payload, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logger = setup_logger(args.log_file)
    start = time.perf_counter()
    logger.info("job start")

    # The version is needed even in the error path, so try to read it early.
    # If the config itself fails, fall back to DEFAULT_VERSION for the error metrics.
    version = DEFAULT_VERSION
    try:
        cfg = load_config(args.config)
        version = cfg.version
        logger.info(
            "config loaded: seed=%s window=%s version=%s", cfg.seed, cfg.window, cfg.version
        )

        df = load_data(args.input)
        logger.info("rows loaded: %s", len(df))

        df = compute_signal(df, cfg.window)
        logger.info("rolling mean + signal computed (window=%s)", cfg.window)

        rows_processed = int(len(df))
        signal_rate = float(df["signal"].mean())
        latency_ms = int(round((time.perf_counter() - start) * 1000))
        logger.info(
            "metrics summary: rows_processed=%s signal_rate=%.4f latency_ms=%s",
            rows_processed,
            signal_rate,
            latency_ms,
        )

        payload = write_success(
            args.output,
            version=version,
            rows_processed=rows_processed,
            signal_rate=signal_rate,
            latency_ms=latency_ms,
            seed=cfg.seed,
        )
        logger.info("job end: success")
        _emit(payload)
        return 0

    except (ConfigError, DataError) as exc:
        logger.error("validation failure: %s", exc)
        extra = {"config_path": str(args.config)} if isinstance(exc, ConfigError) else None
        payload = write_error(
            args.output, version=version, error_message=str(exc), extra=extra
        )
        logger.info("job end: error")
        _emit(payload)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("unexpected failure")
        extra = {"config_path": str(args.config)} if version == DEFAULT_VERSION else None
        payload = write_error(
            args.output,
            version=version,
            error_message=f"{type(exc).__name__}: {exc}",
            extra=extra,
        )
        logger.info("job end: error")
        _emit(payload)
        return 1


if __name__ == "__main__":
    sys.exit(main())
