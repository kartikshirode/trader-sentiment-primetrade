"""Data loading + rolling-mean signal generation for MLOps Task 0.

Decision on warm-up rows: the rolling mean for the first window-1 rows is NaN.
Those rows get signal = 0 so the output is strictly binary, as the spec requires.
The signal_rate metric is computed across the full row count (including warm-up
zeros) to match `rows_processed`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class DataError(ValueError):
    """Raised when the input data file is missing, unreadable, or has the wrong shape."""


def load_data(path: Path) -> pd.DataFrame:
    """Read the OHLCV CSV at path and verify it has a usable `close` column."""
    p = Path(path)
    if not p.exists():
        raise DataError(f"input file not found: {p}")
    if p.stat().st_size == 0:
        raise DataError(f"input file is empty: {p}")
    try:
        df = pd.read_csv(p)
    except pd.errors.EmptyDataError as exc:
        raise DataError(f"input file is empty: {p}") from exc
    except pd.errors.ParserError as exc:
        raise DataError(f"failed to parse CSV: {exc}") from exc
    if df.empty:
        raise DataError(f"input file has zero data rows: {p}")
    if "close" not in df.columns:
        raise DataError(f"input file is missing required column 'close' (got {list(df.columns)})")
    return df


def compute_signal(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Add `rolling_mean` and `signal` columns to df.

    signal = 1 where close > rolling_mean, else 0. Warm-up rows (first window-1)
    have NaN rolling_mean and signal = 0 by convention.
    """
    if window < 1:
        raise DataError(f"window must be >= 1, got {window}")
    # Defensive copy so the caller's DataFrame is never mutated.
    out = df.copy()
    out["rolling_mean"] = out["close"].rolling(window=window, min_periods=window).mean()
    out["signal"] = (out["close"] > out["rolling_mean"]).astype(int)
    return out
