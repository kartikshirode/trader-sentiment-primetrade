"""Trading metric calculators. Each function takes a trade DataFrame and returns a scalar."""
from __future__ import annotations
import numpy as np
import pandas as pd

CRYPTO_PERIODS_PER_YEAR = 365


def pnl_total(df: pd.DataFrame) -> float:
    return float(df["closed_pnl"].sum())


def pnl_mean(df: pd.DataFrame) -> float:
    return float(df["closed_pnl"].mean()) if len(df) else 0.0


def pnl_median(df: pd.DataFrame) -> float:
    return float(df["closed_pnl"].median()) if len(df) else 0.0


def win_rate(df: pd.DataFrame) -> float:
    closes = df[df["closed_pnl"] != 0]
    if len(closes) == 0:
        return float("nan")
    return float((closes["closed_pnl"] > 0).mean())


def profit_factor(df: pd.DataFrame) -> float:
    """Gross profit divided by gross loss.

    Returns inf when a trader has zero losing trades; this is intentional so the row stays flagged as an outlier rather than a NaN.
    """
    pos = df.loc[df["closed_pnl"] > 0, "closed_pnl"].sum()
    neg = df.loc[df["closed_pnl"] < 0, "closed_pnl"].sum()
    if neg == 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / abs(neg))


def sharpe(df: pd.DataFrame, periods_per_year: int = CRYPTO_PERIODS_PER_YEAR) -> float:
    """Annualised Sharpe on the daily PnL series of this trade slice.

    Computed on days the slice actually has trades, so days without trades in this group are excluded.
    """
    if len(df) == 0:
        return float("nan")
    daily = df.groupby("date")["closed_pnl"].sum()
    if len(daily) < 2 or daily.std(ddof=1) == 0:
        return float("nan")
    return float((daily.mean() / daily.std(ddof=1)) * np.sqrt(periods_per_year))


def max_drawdown(df: pd.DataFrame) -> float:
    """Max drawdown of the cumulative daily PnL curve. Returned as a negative number."""
    if len(df) == 0:
        return float("nan")
    daily = df.groupby("date")["closed_pnl"].sum().sort_index().cumsum()
    if len(daily) == 0:
        return float("nan")
    running_max = daily.cummax()
    drawdown = daily - running_max
    return float(drawdown.min())


def trading_frequency(df: pd.DataFrame) -> float:
    """Trades per active day."""
    if len(df) == 0:
        return float("nan")
    active_days = df["date"].nunique()
    return float(len(df) / active_days) if active_days else float("nan")


def roi(df: pd.DataFrame) -> float:
    """Total PnL / total notional traded."""
    notional = df["notional"].sum() if "notional" in df.columns else df["size_usd"].abs().sum()
    if notional == 0:
        return float("nan")
    return float(df["closed_pnl"].sum() / notional)


def risk_proxy(df: pd.DataFrame) -> float:
    """Per-trade PnL standard deviation. Stand-in for proper risk since dataset has no leverage column."""
    if len(df) < 2:
        return float("nan")
    return float(df["closed_pnl"].std(ddof=1))


def all_metrics(df: pd.DataFrame) -> dict:
    return {
        "trades": int(len(df)),
        "pnl_total": pnl_total(df),
        "pnl_mean": pnl_mean(df),
        "pnl_median": pnl_median(df),
        "win_rate": win_rate(df),
        "profit_factor": profit_factor(df),
        "sharpe": sharpe(df),
        "max_drawdown": max_drawdown(df),
        "trading_frequency": trading_frequency(df),
        "roi": roi(df),
        "risk_std": risk_proxy(df),
    }


def metrics_by_group(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for key, sub in df.groupby(group_col, observed=True):
        m = all_metrics(sub)
        m[group_col] = key
        rows.append(m)
    out = pd.DataFrame(rows)
    cols = [group_col] + [c for c in out.columns if c != group_col]
    return out[cols]
