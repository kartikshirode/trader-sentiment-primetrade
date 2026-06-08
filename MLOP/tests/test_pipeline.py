"""Tests for src.pipeline."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.pipeline import DataError, compute_signal, load_data


def test_load_data_missing(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="input file not found"):
        load_data(tmp_path / "nope.csv")


def test_load_data_empty(tmp_path: Path) -> None:
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(DataError, match="empty"):
        load_data(p)


def test_load_data_missing_close(tmp_path: Path) -> None:
    p = tmp_path / "no_close.csv"
    p.write_text("timestamp,open\n2024-01-01,100\n", encoding="utf-8")
    with pytest.raises(DataError, match="missing required column 'close'"):
        load_data(p)


def test_load_data_zero_rows(tmp_path: Path) -> None:
    p = tmp_path / "header_only.csv"
    p.write_text("timestamp,close\n", encoding="utf-8")
    with pytest.raises(DataError, match="zero data rows"):
        load_data(p)


def test_compute_signal_known_fixture() -> None:
    # 10-row hand-built fixture; rolling mean checked by hand for window=3.
    df = pd.DataFrame({"close": [10, 12, 11, 15, 14, 13, 16, 18, 17, 20]})
    out = compute_signal(df, window=3)

    # rolling mean of first 3 rows = 11.0 (10,12,11) -> appears at row index 2
    assert pd.isna(out.loc[0, "rolling_mean"])
    assert pd.isna(out.loc[1, "rolling_mean"])
    assert out.loc[2, "rolling_mean"] == pytest.approx(11.0)
    assert out.loc[3, "rolling_mean"] == pytest.approx((12 + 11 + 15) / 3)

    # signal at row 2: close=11 vs mean=11 -> NOT greater, so 0
    assert out.loc[2, "signal"] == 0
    # signal at row 3: close=15 vs mean=12.67 -> 1
    assert out.loc[3, "signal"] == 1
    # warm-up rows must be 0 (binary contract)
    assert out.loc[0, "signal"] == 0
    assert out.loc[1, "signal"] == 0
    # output column is integer
    assert out["signal"].dtype.kind in {"i", "u"}


def test_compute_signal_invalid_window() -> None:
    df = pd.DataFrame({"close": [1, 2, 3]})
    with pytest.raises(DataError, match="window must be >= 1"):
        compute_signal(df, window=0)


def test_compute_signal_window_one() -> None:
    # With window=1 the rolling mean equals close on every row, so close > rolling_mean
    # is never true. Signal sum must be zero.
    df = pd.DataFrame({"close": [10, 12, 11, 15, 14, 13, 16, 18, 17, 20]})
    out = compute_signal(df, window=1)
    assert out["signal"].sum() == 0
    assert (out["rolling_mean"] == out["close"]).all()


def test_compute_signal_does_not_mutate_input() -> None:
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
    snapshot = df.copy()
    compute_signal(df, window=2)
    pd.testing.assert_frame_equal(df, snapshot)
