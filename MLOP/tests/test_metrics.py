"""Tests for src.metrics."""
from __future__ import annotations

import json
from pathlib import Path

from src.metrics import write_error, write_success


def test_success_shape(tmp_path: Path) -> None:
    out = tmp_path / "metrics.json"
    payload = write_success(
        out,
        version="v1",
        rows_processed=10000,
        signal_rate=0.4990,
        latency_ms=127,
        seed=42,
    )
    assert payload == {
        "version": "v1",
        "rows_processed": 10000,
        "metric": "signal_rate",
        "value": 0.499,
        "latency_ms": 127,
        "seed": 42,
        "status": "success",
    }
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload
    assert set(on_disk.keys()) == {
        "version",
        "rows_processed",
        "metric",
        "value",
        "latency_ms",
        "seed",
        "status",
    }


def test_error_shape(tmp_path: Path) -> None:
    out = tmp_path / "metrics.json"
    payload = write_error(out, version="v1", error_message="missing close column")
    assert payload == {
        "version": "v1",
        "status": "error",
        "error_message": "missing close column",
    }
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload


def test_write_is_atomic(tmp_path: Path) -> None:
    out = tmp_path / "metrics.json"
    write_success(out, version="v1", rows_processed=1, signal_rate=0.5, latency_ms=1, seed=1)
    # no leftover .tmp file should exist after a clean write
    assert not (tmp_path / "metrics.json.tmp").exists()
