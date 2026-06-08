"""Builds the three analysis notebooks under DS/notebooks/."""
from pathlib import Path
import sys

import nbformat as nbf

ROOT = Path(__file__).resolve().parent
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)


def _make(path: Path, cells: list) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nbf.write(nb, str(path))
    print(f"wrote {path}")


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


# ============================================================
# 01_eda.ipynb
# ============================================================

eda = [
    md("""# 01 EDA: Trader Performance vs Bitcoin Sentiment

Cleaned exploratory data analysis on the joined Hyperliquid trades + Bitcoin Fear & Greed Index dataset. The headline regime and trader-ranking results from this notebook feed the v1 report. v2 builds the ML modelling and backtest on top in the next two notebooks.
"""),
    code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.data_loader import load_trades, load_sentiment
from src.features import attach_sentiment, add_trade_features, REGIME_ORDER
from src.metrics import all_metrics, metrics_by_group

sns.set_theme(style='whitegrid', context='talk')
pd.set_option('display.max_columns', 100)

FIG_DIR = Path('../outputs/figures') if Path.cwd().name == 'notebooks' else Path('outputs/figures')
TBL_DIR = Path('../outputs/tables') if Path.cwd().name == 'notebooks' else Path('outputs/tables')
FIG_DIR.mkdir(parents=True, exist_ok=True)
TBL_DIR.mkdir(parents=True, exist_ok=True)

PALETTE = {'Extreme Fear':'#7a0d0d','Fear':'#d0473a','Neutral':'#9a9a9a','Greed':'#3aa05a','Extreme Greed':'#117a3a'}
print('imports ok')
"""),
    md("## Load and join"),
    code("""trades = load_trades()
sent = load_sentiment()
df = attach_sentiment(trades, sent)
df = add_trade_features(df)
print('shape:', df.shape)
print('regime nulls:', df['regime'].isna().sum())
df[['account','coin','date','closed_pnl','size_usd','side','regime','fg_value']].head(3)
"""),
    md("## Regime-level metrics"),
    code("""regime_table = metrics_by_group(df.dropna(subset=['regime']), 'regime')
regime_table = regime_table.set_index('regime').reindex(REGIME_ORDER).reset_index()
regime_table.to_csv(TBL_DIR / 'metrics_by_regime.csv', index=False)
regime_table.round(4)
"""),
    code("""metrics_to_plot = ['pnl_mean','win_rate','profit_factor','sharpe','roi','max_drawdown']
titles = {'pnl_mean':'Avg PnL per trade ($)','win_rate':'Win rate','profit_factor':'Profit factor',
          'sharpe':'Sharpe (annualised)','roi':'ROI','max_drawdown':'Max DD ($)'}
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
for ax, m in zip(axes.flat, metrics_to_plot):
    vals = regime_table.set_index('regime')[m].reindex(REGIME_ORDER)
    ax.bar(vals.index, vals.values, color=[PALETTE[r] for r in vals.index])
    ax.set_title(titles[m], fontsize=12)
    ax.tick_params(axis='x', rotation=20)
plt.tight_layout()
plt.savefig(FIG_DIR / 'metrics_by_regime.png', dpi=140)
plt.show()
plt.close('all')
"""),
    md("## Sentiment timeline"),
    code("""fig, ax = plt.subplots(figsize=(14, 4))
for r, color in PALETTE.items():
    mask = sent['regime'] == r
    ax.scatter(sent.loc[mask,'date'], sent.loc[mask,'fg_value'], s=6, color=color, label=r)
ax.set_title('Fear and Greed Index over time')
ax.set_ylabel('Index value (0 to 100)')
ax.legend(loc='upper left', fontsize=9, ncol=5, frameon=False)
plt.tight_layout()
plt.savefig(FIG_DIR / 'sentiment_timeline.png', dpi=140)
plt.show()
plt.close('all')
"""),
    md("## Cumulative PnL by regime"),
    code("""daily = df.dropna(subset=['regime']).groupby(['date','regime'], observed=True)['closed_pnl'].sum().unstack(fill_value=0)
daily = daily.reindex(columns=REGIME_ORDER, fill_value=0)
cumulative = daily.cumsum()
fig, ax = plt.subplots(figsize=(14, 5))
for r in REGIME_ORDER:
    cumulative[r].plot(ax=ax, color=PALETTE[r], label=r, linewidth=2)
ax.set_title('Cumulative PnL attributable to each regime')
ax.set_ylabel('Cumulative PnL (USD)')
ax.legend(loc='upper left', ncol=5, fontsize=9, frameon=False)
plt.tight_layout()
plt.savefig(FIG_DIR / 'cumulative_pnl_by_regime.png', dpi=140)
plt.show()
plt.close('all')
"""),
]

_make(NB_DIR / "01_eda.ipynb", eda)


# ============================================================
# 02_modeling.ipynb
# ============================================================

modeling = [
    md("""# 02 Modelling: Trader Cohorts + Win-Probability Classifier

Two ML models on the joined dataset:

1. KMeans clustering on per-trader feature vectors to identify trader cohorts.
2. XGBoost classifier predicting the probability that a given close event is a winning trade, conditional on regime, side, size, time of day, trader cohort, and the trader's running win rate.

Both models are persisted as .pkl artefacts under ../models/ for the backtest notebook and the Streamlit dashboard to load.
"""),
    code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.data_loader import load_trades, load_sentiment
from src.features import attach_sentiment, add_trade_features, build_trader_features, REGIME_ORDER
from src.models import (
    fit_cohorts, describe_cohorts, save_cohorts,
    build_winprob_dataset, time_split, fit_winprob, evaluate_winprob, save_winprob,
    DEFAULT_SEED,
)

sns.set_theme(style='whitegrid', context='talk')

ROOT = Path('..') if Path.cwd().name == 'notebooks' else Path('.')
FIG_DIR = ROOT / 'outputs' / 'figures'
TBL_DIR = ROOT / 'outputs' / 'tables'
MODELS_DIR = ROOT / 'models'
for d in (FIG_DIR, TBL_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)
print('ready')
"""),
    md("## Load + join"),
    code("""trades = load_trades()
sent = load_sentiment()
df = attach_sentiment(trades, sent)
df = add_trade_features(df)
print('shape:', df.shape)
"""),
    md("## Trader features + cohort clustering"),
    code("""trader_feats = build_trader_features(df, min_trades=200)
print('active traders (>= 200 trades):', len(trader_feats))
trader_feats.head(3)
"""),
    code("""fit = fit_cohorts(trader_feats, seed=DEFAULT_SEED)
print(f'k = {fit.k},  silhouette = {fit.silhouette:.3f}')
print('cohort sizes:')
print(fit.labels.value_counts().sort_index().to_dict())
save_cohorts(fit, MODELS_DIR / 'cohort_kmeans.pkl', MODELS_DIR / 'cohort_labels.csv')
"""),
    code("""desc = describe_cohorts(trader_feats, fit.labels)
desc.to_csv(TBL_DIR / 'cohort_description.csv')
desc.round(3)
"""),
    md("## Win-probability classifier"),
    code("""closes = df[df['closed_pnl'] != 0].dropna(subset=['regime']).copy()
print('close events:', len(closes))

ds = build_winprob_dataset(closes, fit.labels)
train, test = time_split(ds, frac=0.8)
print('train:', len(train), 'test:', len(test))
print('class balance (train):', train['__label__'].mean().round(3), 'win rate')

model = fit_winprob(train, seed=DEFAULT_SEED)
res = evaluate_winprob(model, test)
print(f'\\noverall AUC = {res[\"overall_auc\"]:.4f}')
print('\\nper-regime AUC:')
print(res['per_regime'].round(4).to_string(index=False))

# persist
save_winprob(model, MODELS_DIR / 'winprob_xgb.pkl')

# eval table
eval_tbl = pd.DataFrame([{'slice': 'overall', 'n': len(test), 'auc': res['overall_auc']}])
eval_tbl = pd.concat([eval_tbl, res['per_regime']], ignore_index=True)
eval_tbl.to_csv(TBL_DIR / 'model_eval.csv', index=False)
eval_tbl.round(4)
"""),
    md("## Calibration plot"),
    code("""from sklearn.calibration import calibration_curve
prob_true, prob_pred = calibration_curve(res['y_true'], res['proba'], n_bins=10)
fig, ax = plt.subplots(figsize=(7, 6))
ax.plot([0,1],[0,1],'--', color='grey', label='perfect')
ax.plot(prob_pred, prob_true, marker='o', color='#3a6ea0', label='model')
ax.set_xlabel('predicted win probability')
ax.set_ylabel('observed win rate')
ax.set_title('Win-probability calibration on test slice')
ax.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / 'winprob_calibration.png', dpi=140)
plt.show()
plt.close('all')
"""),
    md("## Feature importance"),
    code("""drop = {'__ts__','__label__','__account__'}
feat_cols = [c for c in test.columns if c not in drop]
importances = model.feature_importances_
order = np.argsort(importances)[::-1][:10]
imp_df = pd.DataFrame({'feature':[feat_cols[i] for i in order], 'importance':importances[order]})

fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(imp_df['feature'][::-1], imp_df['importance'][::-1], color='#3a6ea0')
ax.set_title('Top 10 feature importances (win-probability model)')
plt.tight_layout()
plt.savefig(FIG_DIR / 'winprob_feature_importance.png', dpi=140)
plt.show()
plt.close('all')
imp_df
"""),
]

_make(NB_DIR / "02_modeling.ipynb", modeling)


# ============================================================
# 03_backtest.ipynb
# ============================================================

backtest = [
    md("""# 03 Backtest: Regime-Rule Strategy

Walk-forward backtest on the last 20% of the dataset (matching the modelling test slice). The rule: take a trade only if the model says win probability is high enough AND the regime is not in the exclusion set. Compared against the take-everything baseline.
"""),
    code("""import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.data_loader import load_trades, load_sentiment
from src.features import attach_sentiment, add_trade_features, build_trader_features
from src.models import build_winprob_dataset, time_split, load_cohorts, load_winprob
from src.backtest import run_backtest

sns.set_theme(style='whitegrid', context='talk')

ROOT = Path('..') if Path.cwd().name == 'notebooks' else Path('.')
FIG_DIR = ROOT / 'outputs' / 'figures'
TBL_DIR = ROOT / 'outputs' / 'tables'
MODELS_DIR = ROOT / 'models'
"""),
    md("## Rebuild test slice with model predictions"),
    code("""trades = load_trades()
sent = load_sentiment()
df = attach_sentiment(trades, sent)
df = add_trade_features(df)

trader_feats = build_trader_features(df, min_trades=200)
cohort_bundle = load_cohorts(MODELS_DIR / 'cohort_kmeans.pkl')
cohort_labels = pd.read_csv(MODELS_DIR / 'cohort_labels.csv').set_index('account')['cohort']

closes = df[df['closed_pnl'] != 0].dropna(subset=['regime']).copy()
ds = build_winprob_dataset(closes, cohort_labels)
train, test = time_split(ds, frac=0.8)

model = load_winprob(MODELS_DIR / 'winprob_xgb.pkl')
drop = {'__ts__','__label__','__account__'}
X_test = test.drop(columns=[c for c in drop if c in test.columns]).values
proba_test = model.predict_proba(X_test)[:, 1]

# build a trades frame aligned with proba_test
closes_sorted = closes.sort_values('ts').reset_index(drop=True)
test_idx = closes_sorted.index[len(train):]
trades_test = closes_sorted.iloc[test_idx].copy()
trades_test['cohort'] = trades_test['account'].map(cohort_labels).fillna(-1).astype(int)
print('test slice:', len(trades_test))
"""),
    md("## Run the backtest"),
    code("""result = run_backtest(
    trades_test,
    proba_test,
    min_winprob=0.60,
    exclude_regimes=['Greed'],
)
summary = result.to_summary()
print('strategy: min_winprob=0.60, exclude Greed')
for k, v in summary.items():
    print(f'  {k}: {v}')

pd.DataFrame([summary]).to_csv(TBL_DIR / 'backtest_summary.csv', index=False)
"""),
    md("## Equity curves"),
    code("""fig, ax = plt.subplots(figsize=(14, 5))
result.equity_baseline.plot(ax=ax, label='baseline (take all)', color='#9a9a9a', linewidth=2)
result.equity_strategy.plot(ax=ax, label='strategy (regime + winprob filter)', color='#117a3a', linewidth=2)
ax.set_title('Backtest equity curves')
ax.set_ylabel('Cumulative PnL (USD)')
ax.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / 'backtest_equity.png', dpi=140)
plt.show()
plt.close('all')
"""),
    md("## Sensitivity: vary min_winprob"),
    code("""rows = []
for mp in [0.50, 0.55, 0.60, 0.65, 0.70]:
    r = run_backtest(trades_test, proba_test, min_winprob=mp, exclude_regimes=[])
    rows.append({'min_winprob': mp, **r.to_summary()})
sens = pd.DataFrame(rows)
sens.to_csv(TBL_DIR / 'backtest_sensitivity.csv', index=False)
sens
"""),
]

_make(NB_DIR / "03_backtest.ipynb", backtest)

print('\nall three notebooks written.')
