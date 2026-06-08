# Trader Performance vs Bitcoin Sentiment (v2)

Primetrade.ai DS submission v2. Joins 211k Hyperliquid trades to the daily Bitcoin Fear and Greed Index, ranks traders, fits two ML models (cohort clustering and a per-trade win-probability classifier), runs a walk-forward backtest, and ships an interactive Streamlit dashboard.

## Headline numbers

- **Extreme Greed regime** posts the highest profitability across every metric (win rate 89.2 %, profit factor 11.0, ROI 2.18 %).
- **Plain Greed regime** is the worst by Sharpe (3.41) and drawdown ($-419k).
- **Win-probability model** clears AUC 0.81 in Extreme Fear, AUC 0.49 in plain Fear; the model is most useful as an extreme-zone filter.
- **Strategy backtest** (regime filter + win-prob filter) ships +13.5 % more PnL on half the trades, Sharpe 14.6 vs 6.6 baseline, zero drawdown.

Full writeup in [outputs/report.md](outputs/report.md).

## Run it

One-shot (PowerShell):

```
pip install -r requirements.txt
./run_all.ps1
streamlit run app/streamlit_app.py
```

Step-by-step (any shell):

```
pip install -r requirements.txt
python -c "from src.data_loader import download_raw; download_raw()"
python build_notebooks.py
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --output 01_eda.ipynb --ExecutePreprocessor.timeout=600
jupyter nbconvert --to notebook --execute notebooks/02_modeling.ipynb --output 02_modeling.ipynb --ExecutePreprocessor.timeout=600
jupyter nbconvert --to notebook --execute notebooks/03_backtest.ipynb --output 03_backtest.ipynb --ExecutePreprocessor.timeout=600
streamlit run app/streamlit_app.py
```

If `gdown` rate-limits, download the two CSVs manually from the assignment Drive links and place them at `data/raw/historical_trades.csv` and `data/raw/fear_greed.csv`.

Security note: only load `.pkl` model files produced by this codebase. Pickle deserialisation runs arbitrary code, so do not unpickle files from untrusted sources.

## Folder layout

```
DS/
  src/
    data_loader.py        gdown + load helpers
    features.py           join + trader-feature engineering
    metrics.py            PnL, win rate, profit factor, Sharpe, MDD, ROI
    models.py             cohort KMeans + win-probability XGBoost
    backtest.py           regime-rule strategy backtester
  notebooks/
    01_eda.ipynb          EDA + regime tables + figures
    02_modeling.ipynb     fit + persist both models, diagnostics
    03_backtest.ipynb     walk-forward backtest + sensitivity sweep
  app/
    streamlit_app.py      3-page interactive dashboard
  models/                 cohort_kmeans.pkl, cohort_labels.csv, winprob_xgb.pkl
  outputs/
    figures/              PNG diagnostics
    tables/               CSV result tables
    report.md             written report (also rendered to PDF/DOCX in submission/)
  tests/                  pytest suite (metrics, models, backtest)
  submission_v1/          original v1 submission preserved as backup
  submission_v2/          rendered v2 deliverables: report.pdf, report.docx, report_full.md, copies of the key figures
  data/raw/               source CSVs (gitignored, auto-downloaded)
  build_notebooks.py      regenerates the three notebooks from scratch
  run_all.ps1             one-shot pipeline runner (PowerShell)
  requirements.txt
  README.md
```

## Tests

```
pytest -q
```

16 tests covering metric correctness against hand-computed values, cohort model determinism + label-count sanity, win-probability model signal on synthetic data + deterministic predictions across seeds, and backtest filter logic (threshold, regime exclusion, cohort filter, length-mismatch error).

## Submission

Push `DS/` as a public GitHub repo, paste the URL into the Google Form. The Streamlit app is part of the repo, so the reviewer can clone + `streamlit run app/streamlit_app.py` themselves. Optional: deploy to Streamlit Community Cloud and include the live URL too.

## v1 backup

The previous submission (notebook, report.docx, figures) lives unchanged under `submission_v1/`. Untouched for reference.
