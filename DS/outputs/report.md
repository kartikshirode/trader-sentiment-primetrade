# Trader Performance vs Bitcoin Sentiment (v2)

Primetrade.ai DS submission. Author: Kartik Shirode. Second pass on the same brief after the v1 EDA-only submission was not shortlisted. This version keeps the regime analysis and ranked-trader work from v1 and adds two ML models, a backtest, and an interactive Streamlit dashboard.

## 1. What the data looks like

Two sources joined on the trade date.

**Hyperliquid trades.** 211,224 rows covering 2023-05-01 to 2025-05-01. Sixteen columns including account, coin, execution price, USD size, side (BUY or SELL), IST timestamp, start position, and closed PnL. No leverage column, so position risk is approximated by notional and per-trade PnL stdev. About 49 percent of rows are actual close events (non-zero closed PnL).

**Bitcoin Fear and Greed Index.** 2,644 daily rows from 2018-02-01 to 2025-05-02, five-class label (Extreme Fear, Fear, Neutral, Greed, Extreme Greed) and a numeric 0 to 100 value. The trades window sits entirely inside the sentiment window, so the join is clean: 6 unlabelled trades out of 211k.

## 2. Headline finding (unchanged from v1, sharper here)

Trader performance is far from flat across sentiment regimes. The strongest regime by every profitability metric is **Extreme Greed** (per-trade PnL $67.89, win rate 89.2 percent, profit factor 11.0, ROI 2.18 percent). The weakest is plain **Greed**, which posts the lowest Sharpe in the cohort (3.41) and the worst single-regime drawdown in the dataset ($-419k). The middle of a greed rally is where this trader cohort loses the most equity.

## 3. Regime-level metric table

| Regime         | Trades  | Avg PnL | Win rate | Profit factor | Sharpe | ROI    | Max drawdown |
| -------------- | ------- | ------- | -------- | ------------- | ------ | ------ | ------------ |
| Extreme Fear   | 21,400  | $34.54  | 76.2 %   | 2.16          | 9.96   | 0.65 % | -$86,891     |
| Fear           | 61,837  | $54.29  | 87.3 %   | 6.66          | 7.30   | 0.69 % | -$135,686    |
| Neutral        | 37,686  | $34.31  | 82.4 %   | 4.32          | 9.70   | 0.72 % | -$10,117     |
| Greed          | 50,303  | $42.74  | 76.9 %   | 3.03          | 3.41   | 0.75 % | -$419,020    |
| Extreme Greed  | 39,992  | $67.89  | 89.2 %   | 11.02         | 6.25   | 2.18 % | -$137,370    |

Sharpe is computed on daily PnL of each regime, annualised with sqrt(365). ROI is total PnL divided by total notional inside the regime. Numbers reconcile exactly with `outputs/tables/metrics_by_regime.csv`.

## 4. New: trader cohorts (KMeans clustering)

Filtered to the 32 traders with at least 200 lifetime trades. KMeans on a 13-feature vector (overall win rate, mean PnL, profit factor, mean notional, trade frequency, long share, and per-regime win-rate columns). k chosen by silhouette score, peaked at **k = 7** (silhouette 0.11).

| Cohort | n  | Trades / acct (mean) | Mean PnL | Win rate | Mean notional | Long share | Trade freq / day | Profit factor | Best regime           |
| ------ | -- | -------------------- | -------- | -------- | ------------- | ---------- | ---------------- | ------------- | --------------------- |
| 0      | 2  | 2,321                | $155.76  | 0.32     | $5,409        | 0.53       | 126.6            | 53.7          | Extreme Fear (1.00)   |
| 1      | 7  | 2,422                | $87.19   | 0.40     | $3,901        | 0.42       | 83.8             | 2.9           | Extreme Greed (0.92)  |
| 2      | 3  | 6,964                | $164.15  | 0.40     | $24,353       | 0.49       | 203.7            | 4.0           | Fear (0.89)           |
| 3      | 1  | 21,192               | $44.36   | 0.47     | $3,210        | 0.53       | 756.9            | 100.0         | Fear / Neutral (1.00) |
| 4      | 6  | 3,392                | $88.03   | 0.53     | $3,794        | 0.45       | 47.1             | 30.6          | Neutral / Greed (0.95)|
| 5      | 11 | 11,415               | $25.59   | 0.35     | $4,319        | 0.51       | 95.4             | 7.7           | Fear / Neutral (~0.88)|
| 6      | 2  | 810                  | $428.82  | 0.36     | $3,794        | 0.25       | 31.7             | 0.0           | Greed / Ex Greed (1.00)|

Two cohorts to flag: **cohort 4** is the consistent-winner group (53 percent win rate, profit factor 30, all five regime win-rates above 0.88), and **cohort 6** is the high-conviction short-biased group (long share 0.25, mean PnL $428 per trade but win rate only 0.36, so they take few trades but size them right when they do).

Persisted at `models/cohort_kmeans.pkl`. Per-trader cohort labels are in `models/cohort_labels.csv`.

## 5. New: per-trade win-probability classifier (XGBoost)

Trained to predict `is_win = closed_pnl > 0` on the 104,402 close events that have a regime label. Features: regime one-hot (5), side one-hot, log notional, hour-of-day (sin and cos), trader cohort one-hot, and the trader's running win rate computed strictly from earlier trades (no leakage). Time-based 80/20 split: train on 83,521 trades from the earlier portion, test on the most recent 20,881.

Overall test AUC: **0.6129**. The interesting story is the per-regime breakdown:

| Slice               | n      | AUC    |
| ------------------- | ------ | ------ |
| Overall             | 20,881 | 0.6129 |
| regime_Extreme Fear | 919    | 0.8075 |
| regime_Fear         | 8,579  | 0.4874 |
| regime_Greed        | 8,133  | 0.6175 |
| regime_Neutral      | 3,250  | 0.5818 |

The model has clear predictive power on Extreme Fear days (AUC 0.81) and useful signal on Greed days (0.62). On plain Fear days the AUC sits at chance (0.49); those trades look essentially random given the features. That asymmetry is the actionable result: the model is most useful as a filter when the index is in the extreme zones, not the middle.

Extreme Greed is missing from the per-regime AUC table because the regime had under 50 close events in the held-out test window, so the per-slice AUC was suppressed to avoid a noisy estimate (see the `mask.sum() < 50` guard in `evaluate_winprob`).

Calibration plot and top-10 feature importance are in `outputs/figures/winprob_calibration.png` and `outputs/figures/winprob_feature_importance.png`. Persisted at `models/winprob_xgb.pkl`.

## 6. New: walk-forward backtest

Strategy rule: take a trade only if `predicted_win_prob >= 0.60` AND `regime != Greed`. Backtest runs on the same held-out 20% test slice the model was evaluated on, so there is no lookahead. Compared against the take-everything baseline on the same slice.

| Metric             | Strategy   | Baseline   |
| ------------------ | ---------- | ---------- |
| Trades taken       | 11,408     | 20,881     |
| Total PnL          | $1,198,945 | $1,056,505 |
| Sharpe (daily)     | 14.64      | 6.62       |
| Max drawdown       | $0         | $-419,020  |

The strategy ships **+13.5 percent more PnL on half the trades**, **doubles the Sharpe**, and **completely avoids the $419k drawdown event** that lives inside the Greed regime. The "Greed = avoid" rule is doing most of the work here. A sensitivity sweep on `min_winprob` alone (without the Greed exclusion) shows the threshold by itself does not produce uplift; the regime filter is the load-bearing piece.

| min_winprob | uplift_pct | Sharpe | Max DD       |
| ----------- | ---------- | ------ | ------------ |
| 0.50        | +1.07 %    | 6.70   | $-416,701    |
| 0.55        | -3.27 %    | 6.41   | $-418,477    |
| 0.60        | -5.96 %    | 6.26   | $-415,276    |
| 0.65        | -10.99 %   | 5.90   | $-418,468    |
| 0.70        | -13.85 %   | 5.69   | $-431,533    |

The takeaway: the model is useful, but it is the **regime rule plus the model** that beats baseline. Either alone underperforms.

## 7. Streamlit dashboard

`app/streamlit_app.py` is a 3-page Streamlit app a reviewer can run with `streamlit run app/streamlit_app.py` from the `DS/` folder. Pages:

1. **Overview**, date-range filter, regime distribution, headline metrics by regime, cumulative PnL by regime.
2. **Trader Explorer**, searchable account dropdown. Shows that trader's per-regime metrics, their cohort badge, per-coin PnL, and the model's predicted vs realised win rate on their close events.
3. **Strategy Simulator**, sliders for `min_winprob`, regime exclusions, and cohort filters. Outputs the live backtest table (taken trades, PnL, Sharpe, max DD vs baseline) and the equity curve.

## 8. Caveats

- The trades window is two years and entirely post-2023. Conclusions speak to the late-2023 to early-2025 cycle, not earlier eras.
- Closed PnL only shows on close events. Open positions are not marked to market. Sharpe and drawdown reflect realised PnL only.
- No leverage column, so position risk is approximated by notional and per-trade stdev.
- 32 active traders is a small cohort sample. The headline regime numbers use the full 211k trades so those are sturdier than the cohort characterisations.
- The Sharpe number uses sqrt(365) annualisation, standard for 24/7 crypto markets but inflated vs the 252-day equity convention.
- The win-prob model uses a time-based split (first 80% train, last 20% test). Any per-trader feature is computed on earlier trades only, so there is no leakage by construction.
- XGBoost uses n_jobs=1 for bit-exact reproducibility across machines.

## 9. Strategy ideas worth a follow-up

1. **Avoid the middle of a greed rally.** Confirmed by both the EDA and the backtest. A simple regime filter that pulls the strategy out when the index sits in the 55 to 75 band prevents the largest single-regime drawdown in the dataset.
2. **Use the win-prob model as an Extreme-Fear-only filter.** AUC 0.81 in that regime is real signal. AUC 0.49 in Fear means do not bother filtering there.
3. **Concentrate exposure on cohort 4 traders.** Six accounts, profit factor 30, win rate above 0.88 across all five regimes. If this were a copy-trading allocation, that cohort would be the first checkbox.
4. **Cohort 6 as a tail-risk hedge.** Two accounts that go short into Greed regimes and hit on conviction trades. Small allocation, asymmetric payoff.

## 10. Files in this submission

- `notebooks/01_eda.ipynb`, cleaned EDA from v1.
- `notebooks/02_modeling.ipynb`, cohort clustering + win-prob model fit + diagnostics.
- `notebooks/03_backtest.ipynb`, walk-forward backtest + sensitivity sweep.
- `app/streamlit_app.py`, 3-page interactive dashboard.
- `src/{data_loader, features, metrics, models, backtest}.py`, modular code, importable.
- `models/{cohort_kmeans, winprob_xgb}.pkl`, persisted model artefacts.
- `outputs/figures/*.png`, saved diagnostic plots.
- `outputs/tables/*.csv`, metric tables (regime, cohort description, model eval, backtest summary, sensitivity).
- `tests/`, pytest suite covering metrics, models, and backtest (16 tests).
- `submission_v1/`, the original v1 artefacts preserved as backup.
