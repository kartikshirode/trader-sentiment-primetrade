"""Trading metric calculators (unchanged from v1)."""
from __future__ import annotations

import numpy as np
import pandas as pd

CRYPTO_PERIODS_PER_YEAR = 365


def pnl_total(df): return float(df["closed_pnl"].sum())
def pnl_mean(df): return float(df["closed_pnl"].mean()) if len(df) else 0.0
def pnl_median(df): return float(df["closed_pnl"].median()) if len(df) else 0.0


def win_rate(df):
    closes = df[df["closed_pnl"] != 0]
    if len(closes) == 0:
        return float("nan")
    return float((closes["closed_pnl"] > 0).mean())


def profit_factor(df):
    """Gross profit / gross loss. Returns inf when there are no losing trades."""
    pos = df.loc[df["closed_pnl"] > 0, "closed_pnl"].sum()
    neg = df.loc[df["closed_pnl"] < 0, "closed_pnl"].sum()
    if neg == 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / abs(neg))


def sharpe(df, periods_per_year=CRYPTO_PERIODS_PER_YEAR):
    """Annualised Sharpe on daily PnL of this slice. Excludes days with no trades."""
    if len(df) == 0:
        return float("nan")
    daily = df.groupby("date")["closed_pnl"].sum()
    if len(daily) < 2 or daily.std(ddof=1) == 0:
        return float("nan")
    return float((daily.mean() / daily.std(ddof=1)) * np.sqrt(periods_per_year))


def max_drawdown(df):
    if len(df) == 0:
        return float("nan")
    daily = df.groupby("date")["closed_pnl"].sum().sort_index().cumsum()
    if len(daily) == 0:
        return float("nan")
    return float((daily - daily.cummax()).min())


def trading_frequency(df):
    if len(df) == 0:
        return float("nan")
    active = df["date"].nunique()
    return float(len(df) / active) if active else float("nan")


def roi(df):
    notional = df["notional"].sum() if "notional" in df.columns else df["size_usd"].abs().sum()
    if notional == 0:
        return float("nan")
    return float(df["closed_pnl"].sum() / notional)


def risk_proxy(df):
    if len(df) < 2:
        return float("nan")
    return float(df["closed_pnl"].std(ddof=1))


def all_metrics(df):
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


def metrics_by_group(df, group_col):
    rows = []
    for key, sub in df.groupby(group_col, observed=True):
        m = all_metrics(sub)
        m[group_col] = key
        rows.append(m)
    out = pd.DataFrame(rows)
    cols = [group_col] + [c for c in out.columns if c != group_col]
    return out[cols]
