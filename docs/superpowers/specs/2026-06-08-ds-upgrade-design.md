# DS Upgrade v2 (Primetrade.ai) Design

Date: 2026-06-08
Status: approved by user
Project root: `DS/`

## Context

The v1 DS submission was rejected without feedback. Public successful submissions on GitHub stay at the EDA + insights level (no ML, no dashboard). The v2 upgrade aims to clear that bar by a wide margin: keep the strong EDA from v1, add a real ML predictive component, add an interactive Streamlit dashboard, ship a refreshed written report. The v1 artifacts get preserved under `submission_v1/` for backup.

## File layout

```
DS/
  submission_v1/                 v1 artifacts (notebook, report.docx, figures, raw data)
  src/
    __init__.py
    data_loader.py               unchanged from v1
    features.py                  v1 + per-trader feature vector for ML
    metrics.py                   unchanged from v1
    models.py                    NEW: cohort KMeans + win-prob XGBoost
    backtest.py                  NEW: simple regime-rule backtester
  notebooks/
    01_eda.ipynb                 cleaned v1 analysis
    02_modeling.ipynb            NEW: fit + evaluate the two models
    03_backtest.ipynb            NEW: walk-forward strategy backtest
  app/
    streamlit_app.py             NEW: 3-page dashboard
  models/                        persisted .pkl artifacts
  outputs/
    figures/                     regenerated EDA charts + model diagnostics
    tables/                      ranked traders + model evaluation tables
    report.md                    refreshed writeup
    report.pdf / report.docx     pandoc renders
  tests/
    test_metrics.py
    test_models.py               NEW: shape + determinism
    test_backtest.py             NEW: known I/O check
  data/raw/                      gitignored, downloaded via gdown on first run
  requirements.txt
  README.md
```

## Two ML models

### Model 1: Trader cohort clustering (KMeans)

- Inputs: per-trader feature vector (win_rate, mean_pnl, profit_factor, sharpe, trade_freq, mean_notional, long_share, per-regime win-rate vector). Filter to traders with at least 200 lifetime trades.
- Pipeline: `StandardScaler` then `KMeans` with k chosen by silhouette score (try k in 3..8, pick the peak).
- Persisted artefacts: `models/cohort_kmeans.pkl` (the pipeline), `models/cohort_labels.csv` (account, cohort_id).
- Characterise each cluster in 1-2 sentences in the report based on mean feature values.

### Model 2: Per-trade win-probability classifier (XGBoost)

- Label: `is_win = closed_pnl > 0`, restricted to close events (non-zero closed_pnl) for ~104k usable rows.
- Features: regime (one-hot, 5 cols), side (one-hot), `log1p(notional)`, hour-of-day (sin/cos pair), trader cohort id (one-hot from Model 1), trader's historical win-rate computed on a strictly earlier window (no leakage).
- Split: time-based, first 80% train, last 20% test. No random shuffle.
- Evaluation: AUC overall, AUC per regime, calibration plot, top-10 feature importance.
- Persisted: `models/winprob_xgb.pkl`, `outputs/tables/model_eval.csv`.
- Determinism: pass `random_state=42` everywhere and pin the train/test split.

If xgboost install proves painful on Windows, fall back to `sklearn.ensemble.GradientBoostingClassifier`. Both produce comparable results for this problem size.

## Backtest

`src/backtest.py` implements `run_backtest(trades, min_winprob, exclude_regimes, cohort_filter) -> dict`. Logic:

- Mark each close event with the model's predicted win probability.
- A "take" decision: `predicted_winprob >= min_winprob AND regime not in exclude_regimes AND trader_cohort in cohort_filter`.
- Sum PnL across taken trades vs across all trades. Compute Sharpe, max DD, total return for both. Report uplift.
- Walk-forward: same time split as the model (first 80% train, eval on last 20%). The backtest only operates on the test slice so there is no lookahead.

## Streamlit dashboard

Single `app/streamlit_app.py` with three sidebar-selectable pages.

1. **Overview**: regime distribution bar, sentiment timeline scatter, headline metrics table by regime, cumulative PnL by regime line chart. Date range filter at top.
2. **Trader Explorer**: searchable account selectbox. Shows per-regime metrics card, cohort badge, predicted vs realised win rate for that trader, per-coin PnL bar.
3. **Strategy Simulator**: sliders for `min_winprob`, regime multiselect (exclude), cohort multiselect (include). Output: equity curve (strategy vs baseline), uplift vs baseline as a delta metric.

Cache data loads with `@st.cache_data` and model loads with `@st.cache_resource`.

## Refreshed report

Same structure as v1 plus:

- New section "Trader cohorts" with the cluster description table.
- New section "Predictive model" with AUC numbers and feature importance.
- New section "Strategy backtest" with the equity curve and the uplift number.
- Updated "Strategy ideas" tying back to model results.

Tone unchanged: human, no em or en dashes, no AI-template phrasing.

## Tests

- `test_metrics.py` (existing): keep as-is.
- `test_models.py`: cluster fit + predict on a 50-row toy dataset produces a fixed cohort distribution given seed=42. Win-prob classifier produces probabilities in [0, 1] and AUC > 0.5 on a known easy fixture.
- `test_backtest.py`: hand-built 10-row test slice with known predicted probs and a known min_winprob threshold produces an exact taken-trade count and exact PnL.

## Verification before commit

1. `pytest -q` all green.
2. `python notebooks/02_modeling.ipynb` (via nbconvert --execute) runs end-to-end without errors and produces both model .pkl files.
3. `python notebooks/03_backtest.ipynb` runs end-to-end and produces the backtest result table.
4. `streamlit run app/streamlit_app.py` opens, all three pages render without exceptions on a smoke click-through.
5. Em/en dash grep clean across all *.md, *.py files I wrote.
6. Report PDF/DOCX regenerated via pandoc, embeds the new model + backtest charts.

## Out of scope (explicitly skipped)

- Streamlit Community Cloud deploy (user runs locally; deploy link is a "nice to have" they can do post-submission).
- Hyperparameter tuning beyond defaults plus k selection by silhouette.
- Deep learning models. XGBoost is enough for this dataset shape.
- Time-series forecasting on the sentiment series (out of scope of the brief).
