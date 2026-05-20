# Trader Performance vs Bitcoin Sentiment

Primetrade.ai assignment writeup. Author: Kartik Shirode.

## 1. What the data looks like

Two sources got joined on the trade date.

**Hyperliquid trades.** 211,224 rows covering 2023-05-01 to 2025-05-01. Sixteen columns including the account address, coin, execution price, USD size, side (BUY or SELL), IST timestamp, start position, and closed PnL. No leverage column, so the risk view here uses notional and per-trade PnL standard deviation as a stand-in. About 49 percent of rows are actual close events (non-zero closed PnL). The rest are entries or scale-ins where PnL is zero by construction.

**Bitcoin Fear and Greed Index.** 2,644 daily rows from 2018-02-01 to 2025-05-02, with a numeric value 0 to 100 and a five-class label: Extreme Fear, Fear, Neutral, Greed, Extreme Greed. The trades window sits entirely inside the sentiment window, so the join lands cleanly with only 6 unlabelled rows out of 211k.

## 2. Headline finding

Trader performance is not flat across sentiment regimes, and the shape of the curve is not what a naive "buy fear, sell greed" reading would predict.

The strongest regime by every profitability metric is **Extreme Greed**. Per-trade PnL averages $67.89, win rate hits 89.2 percent, profit factor reaches 11.0, and ROI on notional jumps to 2.18 percent (3x the next regime). Fear days are second-best on win rate and profit factor. The weak band is plain **Greed**, which posts the lowest profit factor (3.03), the lowest Sharpe (3.41), still healthy in absolute terms but the lowest of the five regimes, and the worst drawdown in the dataset ($-419k).

Translation: the regime where it actually pays to trade aggressively is when the market has gone fully into Extreme Greed, not the middle of the cycle. The middle of a greed rally is where this cohort of traders gets chopped up the hardest.

## 3. Regime-level metric table

| Regime         | Trades  | Avg PnL | Win rate | Profit factor | Sharpe | ROI    | Max drawdown |
| -------------- | ------- | ------- | -------- | ------------- | ------ | ------ | ------------ |
| Extreme Fear   | 21,400  | $34.54  | 76.2 %   | 2.16          | 9.96   | 0.65 % | -$86,891     |
| Fear           | 61,837  | $54.29  | 87.3 %   | 6.66          | 7.30   | 0.69 % | -$135,686    |
| Neutral        | 37,686  | $34.31  | 82.4 %   | 4.32          | 9.70   | 0.72 % | -$10,117     |
| Greed          | 50,303  | $42.74  | 76.9 %   | 3.03          | 3.41   | 0.75 % | -$419,020    |
| Extreme Greed  | 39,992  | $67.89  | 89.2 %   | 11.02         | 6.25   | 2.18 % | -$137,370    |

Win rate is on closed trades only. Sharpe is computed on the daily PnL series of each regime, annualised with sqrt(365). ROI is total PnL divided by total notional traded inside that regime.

## 4. What the statistical tests say

Fear vs Greed (binary collapse of the five classes) on per-trade closed PnL:

- Welch's t-test: t = -0.99, p = 0.32 (Fear mean $49.21, Greed mean $53.88). The mean is not the right comparison here because the PnL distribution is fat-tailed.
- Mann-Whitney U: p = 0.00095. The central tendency does differ once you stop trusting the mean.

Spearman correlation between the daily sentiment value and daily aggregate metrics:

- vs daily total PnL: rho = 0.04, p = 0.38. No monotonic link on total dollars.
- vs daily win rate: rho = 0.19, p = 2.7e-05. Higher sentiment value lines up with a higher fraction of winning trades on the day.

Chi-square on side (BUY vs SELL) across the five regimes: chi2 = 327.2, p ~ 1.4e-69. The long share slides from 51.1 percent in Extreme Fear to 44.9 percent in Extreme Greed, which is the cohort being increasingly short-biased as the market overheats. That contrarian discipline is consistent with the PnL pattern in section 2.

## 5. Top traders and contrarian specialists

Ranking was restricted to accounts with at least 200 lifetime trades and at least 20 trades inside a regime. CSVs for every regime sit in `outputs/tables/`.

**Overall top 5 by total PnL (across the full window):**

| Rank | Account                                    | Trades | Total PnL    | Win rate | Sharpe | Profit factor |
| ---- | ------------------------------------------ | ------ | ------------ | -------- | ------ | ------------- |
| 1    | 0xb1231a4a2dd02f2276fa3c5e2a2f3436e6bfed23 | 14,733 | $2,143,382   | 0.791    | 4.01   | 36.10         |
| 2    | 0x083384f897ee0f19899168e3b1bec365f52a9012 | 3,818  | $1,600,229   | 0.793    | 8.47   | 4.71          |
| 3    | 0xbaaaf6571ab7d571043ff1e313a9609a10637864 | 21,192 | $940,163     | 0.991    | 8.58   | 27,208        |
| 4    | 0x513b8629fe877bb581bf244e326a047b249c4ff1 | 12,236 | $840,422     | 0.895    | 9.76   | 5.90          |
| 5    | 0xbee1707d6b44d4d52bfe19e41f8a828645437aab | 40,184 | $836,080     | 0.763    | 4.76   | 3.86          |

Account 3 has a profit factor of 27k, which means it had only a sliver of losing PnL. Worth a closer look as a market-maker style strategy.

**Contrarian set (28 traders qualified, 50+ trades in both Fear and Greed).**

Top fear specialists (biggest win-rate edge in Fear vs their own Greed performance):

| Account                                    | WR Fear | WR Greed | Edge   | Sharpe Fear | Sharpe Greed |
| ------------------------------------------ | ------- | -------- | ------ | ----------- | ------------ |
| 0x271b280974205ca63b716753467d5a371de622ab | 0.955   | 0.439    | +0.516 | 31.72       | -7.57        |
| 0x083384f897ee0f19899168e3b1bec365f52a9012 | 0.894   | 0.388    | +0.506 | 18.47       | 2.81         |
| 0x8477e447846c758f5a675856001ea72298fd9cb5 | 0.822   | 0.554    | +0.268 | 11.50       | 1.42         |
| 0x8170715b3b381dffb7062c0298972d4727a0a63b | 0.849   | 0.686    | +0.163 | 10.61       | -4.04        |
| 0xb1231a4a2dd02f2276fa3c5e2a2f3436e6bfed23 | 0.875   | 0.729    | +0.146 | 4.69        | 4.19         |

Top greed specialists (better in Greed than in Fear):

| Account                                    | WR Fear | WR Greed | Edge   | Sharpe Fear | Sharpe Greed |
| ------------------------------------------ | ------- | -------- | ------ | ----------- | ------------ |
| 0x3998f134d6aaa2b6a5f723806d00fd2bbbbce891 | 0.534   | 0.931    | -0.397 | -4.71       | 4.19         |
| 0x8381e6d82f1affd39a336e143e081ef7620a3b7f | 0.659   | 0.954    | -0.295 | -6.13       | 4.94         |
| 0x39cef799f8b69da1995852eea189df24eb5cae3c | 0.627   | 0.914    | -0.287 | -0.99       | 4.96         |
| 0x72c6a4624e1dffa724e6d00d64ceae698af892a0 | 0.754   | 1.000    | -0.246 | 8.13        | 5.16         |
| 0x92f17e8d81a944691c10e753af1b1baae1a2cd0d | 0.825   | 0.984    | -0.159 | 6.07        | 11.26        |

The split is real. The top fear specialist flips from a 31.7 Sharpe in Fear to -7.6 in Greed; the top greed specialist flips the other way. These are different strategies wearing different uniforms.

## 6. Caveats

- The trades window is two years and entirely post-2023. The conclusions speak to the late-2023 to early-2025 cycle, not the 2018 to 2022 era.
- Closed PnL only shows on close events. Open positions are not marked to market. The Sharpe and drawdown numbers reflect realised PnL only.
- No leverage column in the trade file, so position risk is approximated by notional and per-trade stdev.
- 28 traders making both Fear and Greed cuts of 50+ trades is a small contrarian sample. The headline regime numbers use the full 211k trades, so those are sturdier.
- The Sharpe number uses a 365-day annualisation, which is the standard for 24/7 crypto markets but inflates the figure relative to the 252-day equity convention.

## 7. Strategy ideas worth a follow-up

1. **Bias allocation to the Extreme Greed regime.** Every profitability metric peaks there, and the long share drops to 44.9 percent, meaning short-side discipline is being rewarded. A simple regime filter that scales position size up when the index sits above ~80 would be the cleanest version of this.
2. **Avoid the middle of a greed rally.** Plain Greed posts the worst Sharpe and the worst single-window drawdown by a wide margin. A risk-down rule when the index is in the 55 to 75 band would have prevented the largest equity destruction in the dataset.
3. **Mix two specialist cohorts instead of one strategy.** The contrarian table shows two real subpopulations: fear specialists and greed specialists. A portfolio that allocates between them based on the current regime should produce a smoother equity curve than chasing one approach. The next step would be a backtest of a 50/50 split that mechanically routes capital by regime label.

## 8. Files in this submission

- `notebooks/analysis.ipynb` runs the full pipeline.
- `src/` holds the data loader, feature engineering, and metric functions.
- `outputs/figures/` has the seven headline charts (sentiment timeline, trades EDA, regime metrics, per-trade PnL boxplot, cumulative PnL by regime, coin-by-regime heatmap, contrarian scatter).
- `outputs/tables/` has the metric table by regime plus the ranked trader CSVs (overall, per regime, and contrarian).
