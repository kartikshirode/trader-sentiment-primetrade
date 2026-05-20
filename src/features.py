"""Feature engineering and the trades + sentiment join."""
from __future__ import annotations
import pandas as pd

# Fine-grained order for plots / tables.
REGIME_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]

# Collapsed binary view used for the headline t-test cut.
BINARY_MAP = {
    "Extreme Fear": "Fear",
    "Fear": "Fear",
    "Neutral": "Neutral",
    "Greed": "Greed",
    "Extreme Greed": "Greed",
}


def attach_sentiment(trades: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    """Left-join the fear-greed regime onto trades by date."""
    out = trades.merge(sentiment, on="date", how="left")
    out["regime"] = pd.Categorical(out["regime"], categories=REGIME_ORDER, ordered=True)
    out["regime_binary"] = out["regime"].map(BINARY_MAP)
    return out


def add_trade_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per-trade derived columns."""
    df = df.copy()
    df["is_win"] = df["closed_pnl"] > 0
    df["notional"] = df["size_usd"].abs()
    df["side_norm"] = df["side"].str.upper()
    mapped = df["side_norm"].map({"BUY": 1, "SELL": -1})
    if mapped.isna().any():
        print(f"warning: {mapped.isna().sum()} trades with unrecognised side")
    df["signed_size"] = df["size_usd"] * mapped.fillna(0)
    return df


def daily_trader_agg(df: pd.DataFrame) -> pd.DataFrame:
    """Roll per-trade rows up to one row per (account, date)."""
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
