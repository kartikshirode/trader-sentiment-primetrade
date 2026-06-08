"""Atomic metrics.json writer for both success and error paths."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _atomic_write(path: Path, payload: dict) -> None:
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, p)


def write_success(
    path: Path,
    *,
    version: str,
    rows_processed: int,
    signal_rate: float,
    latency_ms: int,
    seed: int,
) -> dict:
    payload = {
        "version": version,
        "rows_processed": int(rows_processed),
        "metric": "signal_rate",
        "value": round(float(signal_rate), 4),
        "latency_ms": int(latency_ms),
        "seed": int(seed),
        "status": "success",
    }
    _atomic_write(path, payload)
    return payload


def write_error(
    path: Path,
    *,
    version: str,
    error_message: str,
    extra: dict | None = None,
) -> dict:
    payload = {
        "version": version,
        "status": "error",
        "error_message": error_message,
    }
    if extra:
        payload.update(extra)
    _atomic_write(path, payload)
    return payload
