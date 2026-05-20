# Primetrade.ai Assignment: Trader Performance vs Bitcoin Sentiment

Analysis of Hyperliquid historical trades against the Bitcoin Fear and Greed Index. Built as a hiring assignment for Primetrade.ai.

## Headline takeaways

- Extreme Greed is the highest-performing regime for this trader cohort: 89.2 percent win rate, profit factor 11.0, ROI 2.18 percent.
- Plain Greed is the worst regime: worst Sharpe (3.41) and worst drawdown ($-419k).
- Long share drops from 51.1 percent in Extreme Fear to 44.9 percent in Extreme Greed (chi-square p < 1e-68).
- 28 traders qualify for a Fear-vs-Greed contrarian analysis; some show 50+ point win-rate gaps between regimes.

Full writeup in [outputs/report.md](outputs/report.md).

## Folder layout

```
Primetrade/
  data/raw/                 source CSVs (downloaded, not committed)
  notebooks/analysis.ipynb  full analysis pipeline
  src/                      reusable helpers
    data_loader.py          gdown + load_trades / load_sentiment
    features.py             join + per-trade features
    metrics.py              PnL, win rate, profit factor, Sharpe, max DD, ROI, etc.
  outputs/
    figures/                seven PNGs referenced in the report
    tables/                 ranked trader CSVs + metric-by-regime table
    report.md               written report
  build_notebook.py         regenerates the notebook from scratch
  requirements.txt
  .gitignore
```

## How to reproduce

1. Python 3.10 or newer, then install deps:
   ```
   pip install -r requirements.txt
   ```
2. Pull the source CSVs from Google Drive into `data/raw/`:
   ```python
   from src.data_loader import download_raw
   download_raw()
   ```
3. Run the notebook top to bottom:
   ```
   jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output analysis.ipynb --ExecutePreprocessor.timeout=600
   ```
   Or open it in Jupyter and click Run All.

Outputs land in `outputs/figures/` and `outputs/tables/`. The notebook is idempotent.

## Datasets

- Hyperliquid historical trades: 211,224 rows, 2023-05-01 to 2025-05-01, 16 columns (Account, Coin, Execution Price, Size USD, Side, Timestamp IST, Closed PnL, etc).
- Bitcoin Fear and Greed Index: 2,644 daily rows from 2018-02-01, with a numeric value 0 to 100 and a five-class label.

The trades window sits fully inside the sentiment window. Only 6 of 211k trades land without a regime label after the join.

## Metrics covered

PnL (total, mean, median), win rate, profit factor, Sharpe (daily PnL, annualised with sqrt(365)), max drawdown, trading frequency, ROI on notional, per-trade PnL standard deviation as a risk proxy. The trade file has no leverage column, so position risk is approximated rather than measured directly.

## Notes for the reviewer

- The notebook is structured in 8 sections matching the report.
- All ranked trader tables live in `outputs/tables/`. Contrarian detection is in `contrarian_traders.csv`.
- The contrarian scatter plot (`outputs/figures/contrarian_scatter.png`) shows the Fear vs Greed per-trader PnL split visually.
- Hand-test the metric module with a small DataFrame, for example:
  ```python
  import pandas as pd
  from src.metrics import all_metrics
  sample = pd.DataFrame({
      "closed_pnl": [10.0, -5.0, 7.5, 0.0, 12.0],
      "size_usd": [100, 100, 200, 100, 150],
      "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"]),
  })
  sample["notional"] = sample["size_usd"].abs()
  print(all_metrics(sample))
  ```
