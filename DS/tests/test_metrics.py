"""Lightweight unit tests for src.metrics.

Run from project root:
    python tests/test_metrics.py

No pytest needed. Just assertions plus a final success print.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.metrics import (
    all_metrics,
    win_rate,
    profit_factor,
    sharpe,
    max_drawdown,
    roi,
    pnl_total,
    pnl_mean,
)


def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isinf(a) and math.isinf(b):
        return a == b
    return abs(a - b) <= tol


def make_fixture() -> pd.DataFrame:
    """4 trades across 2 dates. PnL: 10, -5, 7.5, 12. Notional all 100."""
    return pd.DataFrame({
        "closed_pnl": [10.0, -5.0, 7.5, 12.0],
        "size_usd":   [100.0, 100.0, 100.0, 100.0],
        "notional":   [100.0, 100.0, 100.0, 100.0],
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]),
    })


def test_basic_metrics():
    df = make_fixture()
    m = all_metrics(df)

    # Manual expected values
    # pnl_total = 10 - 5 + 7.5 + 12 = 24.5
    # pnl_mean = 24.5 / 4 = 6.125
    # win_rate = 3 wins (10, 7.5, 12) over 4 non-zero closes = 0.75
    # profit_factor = (10+7.5+12) / 5 = 29.5 / 5 = 5.9
    # roi = 24.5 / 400 = 0.06125
    assert approx(m["pnl_total"], 24.5), m["pnl_total"]
    assert approx(m["pnl_mean"], 6.125), m["pnl_mean"]
    assert approx(m["win_rate"], 0.75), m["win_rate"]
    assert approx(m["profit_factor"], 5.9), m["profit_factor"]
    assert approx(m["roi"], 0.06125), m["roi"]

    # daily pnl: day1 = 5, day2 = 19.5. mean = 12.25, std = sqrt(((5-12.25)^2 + (19.5-12.25)^2)/1) = sqrt(105.125) = 10.2530...
    # sharpe = 12.25 / 10.2530... * sqrt(365)
    daily = df.groupby("date")["closed_pnl"].sum()
    expected_sharpe = (daily.mean() / daily.std(ddof=1)) * math.sqrt(365)
    assert approx(m["sharpe"], expected_sharpe, tol=1e-6), (m["sharpe"], expected_sharpe)

    # max drawdown: cumulative = [5, 24.5]; running max = [5, 24.5]; drawdown = [0, 0]; min = 0
    assert approx(m["max_drawdown"], 0.0), m["max_drawdown"]


def test_profit_factor_all_positive():
    df = pd.DataFrame({
        "closed_pnl": [1.0, 2.0, 3.0],
        "size_usd": [10.0, 10.0, 10.0],
        "notional": [10.0, 10.0, 10.0],
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    pf = profit_factor(df)
    assert math.isinf(pf) and pf > 0, f"expected +inf, got {pf}"


def test_profit_factor_all_zero():
    df = pd.DataFrame({
        "closed_pnl": [0.0, 0.0, 0.0],
        "size_usd": [10.0, 10.0, 10.0],
        "notional": [10.0, 10.0, 10.0],
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
    })
    pf = profit_factor(df)
    assert math.isnan(pf), f"expected NaN, got {pf}"


def test_win_rate_only_closes_counted():
    # Trades with closed_pnl = 0 should not count in win_rate denominator
    df = pd.DataFrame({
        "closed_pnl": [10.0, 0.0, -5.0, 0.0],
        "size_usd": [100.0, 100.0, 100.0, 100.0],
        "notional": [100.0, 100.0, 100.0, 100.0],
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]),
    })
    wr = win_rate(df)
    # 1 winner out of 2 non-zero closes = 0.5
    assert approx(wr, 0.5), wr


def test_max_drawdown_known_curve():
    # Daily PnL: +10, +5, -20, +2. Cumulative: 10, 15, -5, -3. Running max: 10, 15, 15, 15.
    # Drawdown: 0, 0, -20, -18. Min = -20.
    df = pd.DataFrame({
        "closed_pnl": [10.0, 5.0, -20.0, 2.0],
        "size_usd": [100.0] * 4,
        "notional": [100.0] * 4,
        "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
    })
    mdd = max_drawdown(df)
    assert approx(mdd, -20.0), mdd


def test_roi_zero_notional():
    df = pd.DataFrame({
        "closed_pnl": [10.0],
        "size_usd": [0.0],
        "notional": [0.0],
        "date": pd.to_datetime(["2024-01-01"]),
    })
    r = roi(df)
    assert math.isnan(r), r


def test_sharpe_one_day_is_nan():
    df = pd.DataFrame({
        "closed_pnl": [5.0, 7.0],
        "size_usd": [10.0, 10.0],
        "notional": [10.0, 10.0],
        "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
    })
    s = sharpe(df)
    assert math.isnan(s), s


def main():
    test_basic_metrics()
    test_profit_factor_all_positive()
    test_profit_factor_all_zero()
    test_win_rate_only_closes_counted()
    test_max_drawdown_known_curve()
    test_roi_zero_notional()
    test_sharpe_one_day_is_nan()
    print("all metric tests passed")


if __name__ == "__main__":
    main()
