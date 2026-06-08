"""Tests for src.backtest with hand-built input/output expectations."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest import run_backtest


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "closed_pnl": [10, -5, 8, -2, 15, -10, 6, 4, -3, 12],
            "regime": ["Fear","Greed","Fear","Neutral","Extreme Greed","Greed","Fear","Neutral","Greed","Fear"],
            "account": [f"a{i}" for i in range(10)],
            "cohort": [0,1,0,2,0,1,2,0,1,2],
            "date": pd.to_datetime([
                "2024-01-01","2024-01-01","2024-01-02","2024-01-02","2024-01-03",
                "2024-01-03","2024-01-04","2024-01-04","2024-01-05","2024-01-05",
            ]),
        }
    )


def test_take_all_threshold_zero():
    df = _frame()
    proba = np.ones(10) * 0.99
    r = run_backtest(df, proba, min_winprob=0.0, exclude_regimes=[])
    assert r.taken_trades == 10
    assert r.pnl_strategy == r.pnl_baseline


def test_threshold_filters_correctly():
    df = _frame()
    proba = np.array([0.9, 0.1, 0.8, 0.4, 0.95, 0.2, 0.7, 0.55, 0.3, 0.85])
    r = run_backtest(df, proba, min_winprob=0.6, exclude_regimes=[])
    # rows kept: 0 (0.9), 2 (0.8), 4 (0.95), 6 (0.7), 9 (0.85) -> 5 trades
    assert r.taken_trades == 5
    # PnL: 10 + 8 + 15 + 6 + 12 = 51
    assert r.pnl_strategy == 51
    # baseline PnL: sum of all 10
    assert r.pnl_baseline == 10-5+8-2+15-10+6+4-3+12  # = 35


def test_exclude_regime():
    df = _frame()
    proba = np.ones(10) * 0.99
    r = run_backtest(df, proba, min_winprob=0.0, exclude_regimes=["Greed"])
    # rows with regime != Greed: 8 rows (drop indices 1, 5, 8)
    assert r.taken_trades == 7
    pnl_no_greed = (10 + 8 + (-2) + 15 + 6 + 4 + 12)
    assert r.pnl_strategy == pnl_no_greed


def test_cohort_filter():
    df = _frame()
    proba = np.ones(10) * 0.99
    r = run_backtest(df, proba, min_winprob=0.0, exclude_regimes=[], cohort_filter=[0])
    # cohort 0 rows: indices 0, 2, 4, 7 -> 4 trades
    assert r.taken_trades == 4
    assert r.pnl_strategy == 10 + 8 + 15 + 4


def test_length_mismatch_raises():
    df = _frame()
    proba = np.zeros(5)
    try:
        run_backtest(df, proba)
    except ValueError as e:
        assert "same length" in str(e)
        return
    assert False, "should have raised"


def main():
    test_take_all_threshold_zero()
    test_threshold_filters_correctly()
    test_exclude_regime()
    test_cohort_filter()
    test_length_mismatch_raises()
    print("all backtest tests passed")


if __name__ == "__main__":
    main()
