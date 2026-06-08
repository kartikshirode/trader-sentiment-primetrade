"""Streamlit dashboard for trader-vs-sentiment analysis.

Run from the DS/ folder:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest import run_backtest
from src.data_loader import load_sentiment, load_trades
from src.features import REGIME_ORDER, add_trade_features, attach_sentiment, build_trader_features
from src.metrics import all_metrics, metrics_by_group
from src.models import build_winprob_dataset, load_cohorts, load_winprob, time_split

MODELS_DIR = ROOT / "models"
PALETTE = {
    "Extreme Fear": "#7a0d0d",
    "Fear": "#d0473a",
    "Neutral": "#9a9a9a",
    "Greed": "#3aa05a",
    "Extreme Greed": "#117a3a",
}

st.set_page_config(page_title="Trader vs Sentiment (Primetrade.ai)", layout="wide")


@st.cache_data(show_spinner="Loading data...")
def _load() -> pd.DataFrame | None:
    try:
        t = load_trades()
        s = load_sentiment()
    except FileNotFoundError:
        return None
    df = attach_sentiment(t, s)
    df = add_trade_features(df)
    return df


@st.cache_resource(show_spinner="Loading models...")
def _load_models():
    cohort_path = MODELS_DIR / "cohort_kmeans.pkl"
    winprob_path = MODELS_DIR / "winprob_xgb.pkl"
    labels_path = MODELS_DIR / "cohort_labels.csv"
    if not (cohort_path.exists() and winprob_path.exists() and labels_path.exists()):
        return None, None, None
    cohort_bundle = load_cohorts(cohort_path)
    winprob = load_winprob(winprob_path)
    cohort_labels = pd.read_csv(labels_path).set_index("account")["cohort"]
    return cohort_bundle, winprob, cohort_labels


# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("Trader vs Sentiment")
st.sidebar.caption("Primetrade.ai DS submission v2")

page = st.sidebar.radio("Page", ["Overview", "Trader Explorer", "Strategy Simulator"])

df = _load()
if df is None:
    st.error(
        "Source data missing. Run: "
        "`python -c \"from src.data_loader import download_raw; download_raw()\"`"
    )
    st.stop()
cohort_bundle, winprob_model, cohort_labels = _load_models()

if cohort_labels is None:
    st.sidebar.warning(
        "Models not found. Run `python build_notebooks.py` then execute "
        "`notebooks/02_modeling.ipynb` to generate them."
    )


# ============================================================
# Page 1: Overview
# ============================================================

if page == "Overview":
    st.title("Regime overview")
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    rng = st.slider(
        "Date range", min_value=min_date, max_value=max_date,
        value=(min_date, max_date),
    )
    mask = (df["date"] >= pd.Timestamp(rng[0])) & (df["date"] <= pd.Timestamp(rng[1]) + pd.Timedelta(days=1))
    subset = df[mask].dropna(subset=["regime"]).copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", f"{len(subset):,}")
    c2.metric("Close events", f"{int(subset['is_close'].sum()):,}")
    c3.metric("Total PnL", f"${subset['closed_pnl'].sum():,.0f}")
    c4.metric("Active traders", f"{subset['account'].nunique():,}")

    st.subheader("Trades by regime")
    counts = subset["regime"].value_counts().reindex(REGIME_ORDER).fillna(0)
    counts_df = counts.reset_index()
    counts_df.columns = ["regime", "trades"]
    st.bar_chart(counts_df, x="regime", y="trades", color=None)

    st.subheader("Headline metrics by regime")
    regime_table = metrics_by_group(subset, "regime")
    regime_table = (
        regime_table.set_index("regime").reindex(REGIME_ORDER).reset_index()
    )
    st.dataframe(regime_table.round(4), width="stretch")

    st.subheader("Cumulative PnL by regime")
    daily = (
        subset.groupby(["date", "regime"], observed=True)["closed_pnl"].sum()
        .unstack(fill_value=0).reindex(columns=REGIME_ORDER, fill_value=0).cumsum()
    )
    st.line_chart(daily)


# ============================================================
# Page 2: Trader Explorer
# ============================================================

elif page == "Trader Explorer":
    st.title("Trader explorer")

    if cohort_labels is None:
        st.error("Cohort labels not loaded. Run the modelling notebook first.")
        st.stop()

    candidates = sorted(cohort_labels.index.tolist())
    sel = st.selectbox("Account", candidates, index=0)
    sub = df[df["account"] == sel].dropna(subset=["regime"]).copy()

    cohort_id = int(cohort_labels[sel])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", f"{len(sub):,}")
    c2.metric("Total PnL", f"${sub['closed_pnl'].sum():,.0f}")
    c3.metric("Win rate", f"{(sub.loc[sub['closed_pnl'] != 0, 'closed_pnl'] > 0).mean():.2%}")
    c4.metric("Cohort", f"#{cohort_id}")

    st.subheader("Per-regime metrics for this trader")
    per_regime = metrics_by_group(sub, "regime")
    per_regime = per_regime.set_index("regime").reindex(REGIME_ORDER).reset_index()
    st.dataframe(per_regime.round(4), width="stretch")

    st.subheader("Per-coin PnL")
    coin_pnl = sub.groupby("coin")["closed_pnl"].sum().sort_values(ascending=False).head(15)
    st.bar_chart(coin_pnl)

    if winprob_model is not None:
        st.subheader("Predicted vs realised win rate (on this trader's close events)")
        closes = sub[sub["closed_pnl"] != 0].copy()
        if len(closes) > 0:
            ds = build_winprob_dataset(closes, cohort_labels)
            drop = {"__ts__", "__label__", "__account__"}
            X = ds.drop(columns=[c for c in drop if c in ds.columns]).values
            proba = winprob_model.predict_proba(X)[:, 1]
            realised = float(ds["__label__"].mean())
            predicted = float(proba.mean())
            d1, d2 = st.columns(2)
            d1.metric("Realised win rate", f"{realised:.2%}")
            d2.metric("Model average predicted win prob", f"{predicted:.2%}")


# ============================================================
# Page 3: Strategy Simulator
# ============================================================

elif page == "Strategy Simulator":
    st.title("Strategy simulator")

    if winprob_model is None or cohort_labels is None:
        st.error("Models not loaded. Run the modelling notebook first.")
        st.stop()

    st.caption(
        "Backtest a regime-rule strategy on the held-out 20% time slice from the modelling notebook. "
        "Compares against the take-everything baseline on the same slice."
    )

    min_wp = st.slider("Minimum predicted win probability", 0.0, 1.0, 0.60, 0.05)
    exclude = st.multiselect(
        "Exclude regimes", options=REGIME_ORDER, default=["Greed"]
    )
    cohort_options = sorted(set(int(c) for c in cohort_labels.unique()))
    cohort_pick = st.multiselect(
        "Include cohorts", options=cohort_options, default=cohort_options
    )

    if not cohort_pick:
        st.warning("Select at least one cohort to run the backtest.")
        st.stop()
    if set(exclude) == set(REGIME_ORDER):
        st.warning("All regimes excluded; nothing left to take.")
        st.stop()

    # Rebuild the test slice with predictions
    closes = df[df["closed_pnl"] != 0].dropna(subset=["regime"]).copy()
    ds = build_winprob_dataset(closes, cohort_labels)
    train, test = time_split(ds, frac=0.8)
    drop = {"__ts__", "__label__", "__account__"}
    X = test.drop(columns=[c for c in drop if c in test.columns]).values
    proba = winprob_model.predict_proba(X)[:, 1]

    closes_sorted = closes.sort_values("ts", kind="mergesort").reset_index(drop=True)
    trades_test = closes_sorted.iloc[len(train):].copy()
    trades_test["cohort"] = trades_test["account"].map(cohort_labels).fillna(-1).astype(int)

    result = run_backtest(
        trades_test, proba, min_winprob=min_wp,
        exclude_regimes=exclude, cohort_filter=cohort_pick,
    )

    s = result.to_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades taken", f"{s['taken_trades']:,}", f"of {s['total_trades']:,}")
    c2.metric("Strategy PnL", f"${s['pnl_strategy']:,.0f}", f"{s['uplift_pct']:+.2f}%")
    c3.metric("Sharpe", f"{s['sharpe_strategy']:.2f}", f"vs {s['sharpe_baseline']:.2f}")
    c4.metric("Max DD", f"${s['mdd_strategy']:,.0f}", f"vs ${s['mdd_baseline']:,.0f}")

    st.subheader("Equity curves")
    eq = pd.DataFrame({
        "baseline": result.equity_baseline,
        "strategy": result.equity_strategy,
    }).ffill().fillna(0)
    st.line_chart(eq)
