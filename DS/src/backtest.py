"""Simple regime-rule backtester driven by model outputs."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .metrics import max_drawdown, sharpe


@dataclass
class BacktestResult:
    taken_trades: int
    total_trades: int
    pnl_strategy: float
    pnl_baseline: float
    uplift_pct: float
    sharpe_strategy: float
    sharpe_baseline: float
    mdd_strategy: float
    mdd_baseline: float
    equity_strategy: pd.Series
    equity_baseline: pd.Series

    def to_summary(self) -> dict:
        return {
            "taken_trades": self.taken_trades,
            "total_trades": self.total_trades,
            "pnl_strategy": round(self.pnl_strategy, 2),
            "pnl_baseline": round(self.pnl_baseline, 2),
            "uplift_pct": round(self.uplift_pct, 2),
            "sharpe_strategy": round(self.sharpe_strategy, 3),
            "sharpe_baseline": round(self.sharpe_baseline, 3),
            "mdd_strategy": round(self.mdd_strategy, 2),
            "mdd_baseline": round(self.mdd_baseline, 2),
        }


def run_backtest(
    trades: pd.DataFrame,
    predicted_winprob: np.ndarray,
    min_winprob: float = 0.6,
    exclude_regimes: list[str] | None = None,
    cohort_filter: list[int] | None = None,
) -> BacktestResult:
    """Compare a regime-rule strategy against the take-everything baseline.

    trades: frame with columns closed_pnl, date, regime, account, cohort.
            Length must match predicted_winprob.
    predicted_winprob: per-trade model output, same order as trades.
    """
    if len(trades) != len(predicted_winprob):
        raise ValueError("trades and predicted_winprob must be the same length")
    exclude_regimes = exclude_regimes or []

    t = trades.copy().reset_index(drop=True)
    t["pred"] = np.asarray(predicted_winprob)

    take = t["pred"] >= min_winprob
    take &= ~t["regime"].astype(str).isin(exclude_regimes)
    if cohort_filter is not None and "cohort" in t.columns:
        take &= t["cohort"].isin(cohort_filter)

    strategy = t[take].copy()
    baseline = t

    eq_strategy = strategy.groupby("date")["closed_pnl"].sum().sort_index().cumsum()
    eq_baseline = baseline.groupby("date")["closed_pnl"].sum().sort_index().cumsum()

    pnl_s = float(strategy["closed_pnl"].sum())
    pnl_b = float(baseline["closed_pnl"].sum())
    uplift = float((pnl_s - pnl_b) / abs(pnl_b) * 100.0) if pnl_b != 0 else float("nan")

    return BacktestResult(
        taken_trades=int(take.sum()),
        total_trades=int(len(t)),
        pnl_strategy=pnl_s,
        pnl_baseline=pnl_b,
        uplift_pct=uplift,
        sharpe_strategy=sharpe(strategy) if len(strategy) else float("nan"),
        sharpe_baseline=sharpe(baseline) if len(baseline) else float("nan"),
        mdd_strategy=max_drawdown(strategy) if len(strategy) else float("nan"),
        mdd_baseline=max_drawdown(baseline) if len(baseline) else float("nan"),
        equity_strategy=eq_strategy,
        equity_baseline=eq_baseline,
    )
