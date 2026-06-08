"""ML models: trader cohort clustering + per-trade win-probability classifier."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
    _HAS_XGB = True
except ImportError:  # pragma: no cover
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier  # type: ignore
    _HAS_XGB = False

import joblib

from .features import REGIME_ORDER

DEFAULT_SEED = 42


# ---------- Model 1: trader cohort clustering ----------


@dataclass
class CohortFit:
    pipeline: Pipeline
    k: int
    silhouette: float
    labels: pd.Series  # account -> cohort_id
    feature_cols: list[str]


def select_k(features: pd.DataFrame, k_range: Iterable[int] = range(3, 8), seed: int = DEFAULT_SEED) -> int:
    """Pick k by silhouette score on a fixed scaler."""
    scaler = StandardScaler()
    X = scaler.fit_transform(features.values)
    best_k, best_score = None, -1.0
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = km.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_k, best_score = k, score
    return int(best_k)


def fit_cohorts(features: pd.DataFrame, k: int | None = None, seed: int = DEFAULT_SEED) -> CohortFit:
    """Fit KMeans on the per-trader feature matrix."""
    if k is None:
        k = select_k(features, seed=seed)
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("kmeans", KMeans(n_clusters=k, n_init=10, random_state=seed)),
    ])
    pipe.fit(features.values)
    labels = pd.Series(pipe.named_steps["kmeans"].labels_, index=features.index, name="cohort")
    X_scaled = pipe.named_steps["scaler"].transform(features.values)
    sil = float(silhouette_score(X_scaled, labels.values))
    return CohortFit(pipeline=pipe, k=k, silhouette=sil, labels=labels, feature_cols=list(features.columns))


def describe_cohorts(features: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Mean feature values per cohort, plus size."""
    feats = features.copy()
    feats["cohort"] = labels.values
    desc = feats.groupby("cohort").agg(["mean", "size"])
    # collapse multiindex
    desc.columns = [f"{a}_{b}" if b != "size" else "n" for a, b in desc.columns]
    desc = desc.loc[:, ~desc.columns.duplicated()]
    return desc


def save_cohorts(fit: CohortFit, model_path: Path, labels_path: Path) -> None:
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": fit.pipeline, "k": fit.k, "feature_cols": fit.feature_cols}, model_path)
    fit.labels.reset_index().to_csv(labels_path, index=False)


def load_cohorts(model_path: Path) -> dict:
    return joblib.load(model_path)


# ---------- Model 2: per-trade win-probability classifier ----------


def build_winprob_dataset(df_closes: pd.DataFrame, cohort_labels: pd.Series) -> pd.DataFrame:
    """Assemble the feature matrix for the win-probability model.

    df_closes: trade-level frame with closed_pnl != 0 and engineered features
               (regime, side_norm, log_notional, hour_sin, hour_cos, account, ts).
    cohort_labels: Series of cohort id keyed by account.
    """
    d = df_closes.copy()
    d = d.sort_values("ts").reset_index(drop=True)
    d["cohort"] = d["account"].map(cohort_labels).fillna(-1).astype(int)

    # trader historical win-rate computed strictly on rows before the current one
    d["_running_wins"] = d.groupby("account")["is_win"].cumsum() - d["is_win"].astype(int)
    d["_running_trades"] = d.groupby("account").cumcount()
    d["trader_hist_winrate"] = np.where(
        d["_running_trades"] > 0, d["_running_wins"] / d["_running_trades"], 0.5
    )
    d.drop(columns=["_running_wins", "_running_trades"], inplace=True)

    regime_dummies = pd.get_dummies(d["regime"].astype(str), prefix="regime")
    side_dummies = pd.get_dummies(d["side_norm"], prefix="side")
    cohort_dummies = pd.get_dummies(d["cohort"], prefix="cohort")

    feature_block = pd.concat(
        [
            d[["log_notional", "hour_sin", "hour_cos", "trader_hist_winrate"]].reset_index(drop=True),
            regime_dummies.reset_index(drop=True),
            side_dummies.reset_index(drop=True),
            cohort_dummies.reset_index(drop=True),
        ],
        axis=1,
    )
    feature_block["__ts__"] = d["ts"].values
    feature_block["__label__"] = d["is_win"].astype(int).values
    feature_block["__account__"] = d["account"].values
    return feature_block


def time_split(features: pd.DataFrame, frac: float = 0.8) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Sort by __ts__ and split into train (first frac) and test (last 1-frac)."""
    f = features.sort_values("__ts__").reset_index(drop=True)
    cut = int(len(f) * frac)
    return f.iloc[:cut].copy(), f.iloc[cut:].copy()


def fit_winprob(train: pd.DataFrame, seed: int = DEFAULT_SEED):
    """Fit the win-probability classifier on the train slice."""
    drop = {"__ts__", "__label__", "__account__"}
    X = train.drop(columns=[c for c in drop if c in train.columns]).values
    y = train["__label__"].values
    if _HAS_XGB:
        model = XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=seed,
            n_jobs=-1,
            tree_method="hist",
        )
    else:  # pragma: no cover
        model = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.08, random_state=seed)
    model.fit(X, y)
    return model


def evaluate_winprob(model, test: pd.DataFrame) -> dict:
    drop = {"__ts__", "__label__", "__account__"}
    X = test.drop(columns=[c for c in drop if c in test.columns]).values
    y = test["__label__"].values
    proba = model.predict_proba(X)[:, 1]
    overall_auc = float(roc_auc_score(y, proba)) if len(set(y)) > 1 else float("nan")

    # per-regime AUC
    regime_cols = [c for c in test.columns if c.startswith("regime_")]
    rows = []
    for col in regime_cols:
        mask = test[col].values == 1
        if mask.sum() < 50:
            continue
        y_r = y[mask]
        if len(set(y_r)) < 2:
            continue
        rows.append({"slice": col, "n": int(mask.sum()), "auc": float(roc_auc_score(y_r, proba[mask]))})
    per_regime = pd.DataFrame(rows)
    return {"overall_auc": overall_auc, "per_regime": per_regime, "proba": proba, "y_true": y}


def save_winprob(model, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_winprob(path: Path):
    return joblib.load(path)
