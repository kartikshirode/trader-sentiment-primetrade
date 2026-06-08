"""Feature engineering: trade-level join + per-trader vectors for ML."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

REGIME_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]
BINARY_MAP = {
    "Extreme Fear": "Fear",
    "Fear": "Fear",
    "Neutral": "Neutral",
    "Greed": "Greed",
    "Extreme Greed": "Greed",
}


def attach_sentiment(trades: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    out = trades.merge(sentiment, on="date", how="left")
    out["regime"] = pd.Categorical(out["regime"], categories=REGIME_ORDER, ordered=True)
    out["regime_binary"] = out["regime"].map(BINARY_MAP)
    return out


def add_trade_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_win"] = df["closed_pnl"] > 0
    df["is_close"] = df["closed_pnl"] != 0
    df["notional"] = df["size_usd"].abs()
    df["side_norm"] = df["side"].str.upper()
    mapped = df["side_norm"].map({"BUY": 1, "SELL": -1})
    if mapped.isna().any():
        warnings.warn(
            f"{mapped.isna().sum()} trades with unrecognised side",
            RuntimeWarning,
            stacklevel=2,
        )
    df["signed_size"] = df["size_usd"] * mapped.fillna(0)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["log_notional"] = np.log1p(df["notional"])
    return df


def build_trader_features(df: pd.DataFrame, min_trades: int = 200) -> pd.DataFrame:
    """One row per trader with the metric vector used for clustering.

    Filters to traders with at least min_trades lifetime trades so the
    aggregate stats are meaningful.
    """
    counts = df.groupby("account").size()
    active = counts[counts >= min_trades].index
    d = df[df["account"].isin(active)].copy()

    # Per-regime win rate, pivoted to one column per regime.
    closes = d[d["closed_pnl"] != 0]
    wr_by_regime = (
        closes.groupby(["account", "regime"], observed=True)["is_win"]
        .mean()
        .unstack("regime")
        .reindex(columns=REGIME_ORDER)
        .add_prefix("wr_")
        .fillna(0.0)
    )

    overall = d.groupby("account").agg(
        trades=("closed_pnl", "size"),
        mean_pnl=("closed_pnl", "mean"),
        win_rate=("is_win", "mean"),
        mean_notional=("notional", "mean"),
        active_days=("date", "nunique"),
        long_share=("side_norm", lambda s: float((s == "BUY").mean())),
    )
    overall["trade_freq"] = overall["trades"] / overall["active_days"]

    # Profit factor (gross profit / gross loss)
    pos = d[d["closed_pnl"] > 0].groupby("account")["closed_pnl"].sum()
    neg = d[d["closed_pnl"] < 0].groupby("account")["closed_pnl"].sum().abs()
    overall["profit_factor"] = (pos / neg).replace([np.inf, -np.inf], np.nan).fillna(0).clip(upper=100)

    feats = overall.join(wr_by_regime, how="left").fillna(0.0)
    return feats


def daily_trader_agg(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["account", "date"], observed=True)
    out = g.agg(
        pnl=("closed_pnl", "sum"),
        trades=("closed_pnl", "size"),
        notional=("notional", "sum"),
        fee=("fee", "sum"),
        wins=("is_win", "sum"),
    ).reset_index()
    out["win_rate"] = out["wins"] / out["trades"]
    return out
