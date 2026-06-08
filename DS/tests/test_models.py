"""Tests for src.models: cohort fit + win-prob classifier on toy fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import (
    DEFAULT_SEED,
    build_winprob_dataset,
    evaluate_winprob,
    fit_cohorts,
    fit_winprob,
    time_split,
)


def _trader_features(n: int = 30, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "trades": rng.integers(200, 2000, n),
            "mean_pnl": rng.normal(0, 50, n),
            "win_rate": rng.uniform(0.3, 0.9, n),
            "mean_notional": rng.uniform(100, 5000, n),
            "active_days": rng.integers(5, 60, n),
            "long_share": rng.uniform(0.2, 0.8, n),
            "trade_freq": rng.uniform(1, 50, n),
            "profit_factor": rng.uniform(0.5, 10, n),
            "wr_Extreme Fear": rng.uniform(0.2, 0.9, n),
            "wr_Fear": rng.uniform(0.2, 0.9, n),
            "wr_Neutral": rng.uniform(0.2, 0.9, n),
            "wr_Greed": rng.uniform(0.2, 0.9, n),
            "wr_Extreme Greed": rng.uniform(0.2, 0.9, n),
        },
        index=[f"acct_{i}" for i in range(n)],
    )


def test_cohort_fit_deterministic():
    feats = _trader_features(n=30, seed=0)
    fit_a = fit_cohorts(feats, k=4, seed=DEFAULT_SEED)
    fit_b = fit_cohorts(feats, k=4, seed=DEFAULT_SEED)
    assert (fit_a.labels.values == fit_b.labels.values).all()
    assert fit_a.k == 4
    assert -1.0 <= fit_a.silhouette <= 1.0


def test_cohort_label_count_matches_input():
    feats = _trader_features(n=20, seed=1)
    fit = fit_cohorts(feats, k=3, seed=DEFAULT_SEED)
    assert len(fit.labels) == 20
    assert set(fit.labels.unique()).issubset({0, 1, 2})


def _toy_winprob_dataset() -> pd.DataFrame:
    """Synthetic trades where regime_A wins 80%, regime_B wins 30%, so the model has obvious signal."""
    rng = np.random.default_rng(42)
    n = 400
    regime = rng.choice(["A", "B"], size=n)
    is_win = np.where(
        regime == "A", rng.binomial(1, 0.8, n), rng.binomial(1, 0.3, n)
    )
    df = pd.DataFrame(
        {
            "ts": pd.date_range("2024-01-01", periods=n, freq="h"),
            "account": [f"acct_{i % 10}" for i in range(n)],
            "closed_pnl": np.where(is_win == 1, 10.0, -5.0),
            "regime": regime,
            "side_norm": rng.choice(["BUY", "SELL"], size=n),
            "notional": rng.uniform(50, 500, n),
            "log_notional": np.log1p(rng.uniform(50, 500, n)),
            "hour_sin": rng.uniform(-1, 1, n),
            "hour_cos": rng.uniform(-1, 1, n),
            "is_win": is_win.astype(bool),
            "date": pd.date_range("2024-01-01", periods=n, freq="h").normalize(),
        }
    )
    return df


def test_winprob_signal_above_chance():
    df = _toy_winprob_dataset()
    cohort_labels = pd.Series({a: i % 3 for i, a in enumerate(df["account"].unique())})
    ds = build_winprob_dataset(df, cohort_labels)
    train, test = time_split(ds, frac=0.8)
    model = fit_winprob(train, seed=DEFAULT_SEED)
    res = evaluate_winprob(model, test)
    assert res["overall_auc"] > 0.65, f"toy AUC should clear 0.65, got {res['overall_auc']}"
    assert ((res["proba"] >= 0) & (res["proba"] <= 1)).all()


def test_winprob_deterministic_given_seed():
    df = _toy_winprob_dataset()
    cohort_labels = pd.Series({a: i % 3 for i, a in enumerate(df["account"].unique())})
    ds = build_winprob_dataset(df, cohort_labels)
    train, test = time_split(ds, frac=0.8)
    m1 = fit_winprob(train, seed=DEFAULT_SEED)
    m2 = fit_winprob(train, seed=DEFAULT_SEED)
    drop = {"__ts__", "__label__", "__account__"}
    X = test.drop(columns=[c for c in drop if c in test.columns]).values
    np.testing.assert_allclose(m1.predict_proba(X)[:, 1], m2.predict_proba(X)[:, 1])


def main():
    test_cohort_fit_deterministic()
    test_cohort_label_count_matches_input()
    test_winprob_signal_above_chance()
    test_winprob_deterministic_given_seed()
    print("all model tests passed")


if __name__ == "__main__":
    main()
