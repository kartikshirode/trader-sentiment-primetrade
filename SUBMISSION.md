# How to submit this to Primetrade.ai

Quick guide to filing the assignment through their Google Form. The form usually asks for: name, email, resume link, GitHub link, notebook link, and a written report. This file lines up everything they will ask for.

## What Primetrade expects (verified)

Looking at one accepted submission (Saurabh Pandey, posted on LinkedIn after he submitted), they wanted three artifacts:

1. **GitHub repo link** with the full code, README, notebook, outputs
2. **Notebook link** that opens and runs in the browser (Colab works)
3. **Written report** as PDF or DOCX, attached or linked

The original task brief said "PLEASE SUBMIT THROUGH GOOGLE FORM DOC SHARED NOT BY EMAIL". Resume goes in too.

## Three steps before opening the Google Form

### Step 1: Push this folder to a public GitHub repo

The repo is already a git repo with a clean history. Run these from this folder:

```powershell
# Pick a repo name on GitHub first (e.g. trader-sentiment-primetrade), then:
gh repo create trader-sentiment-primetrade --public --source=. --remote=origin --push
```

If `gh` is not installed: create the repo manually on github.com, then:

```powershell
git remote add origin https://github.com/<your-username>/trader-sentiment-primetrade.git
git branch -M main
git push -u origin main
```

The repo will include: README, notebooks/analysis.ipynb (with executed cell outputs intact, which is what Primetrade wants), src/ modules, outputs/ figures and tables, tests/, the PDF + DOCX in submission/, and report.md in outputs/.

### Step 2: Get a Colab link for the notebook

Two options.

**Option A (recommended, no upload).** Once the GitHub repo is public, the executed notebook will auto-render at:
`https://github.com/<your-username>/trader-sentiment-primetrade/blob/main/notebooks/analysis.ipynb`

To get a "Open in Colab" link, prefix it:
`https://colab.research.google.com/github/<your-username>/trader-sentiment-primetrade/blob/main/notebooks/analysis.ipynb`

This works because Colab can open any public GitHub notebook directly.

**Option B (self-contained Colab).** The file `submission/analysis_colab.ipynb` is a single-file Colab notebook that downloads the data inside the first cell and runs end-to-end without needing the rest of the repo. Upload it to your Google Drive, open with Colab, then share the link with anyone-with-the-link permission.

### Step 3: Pick a report format

Two ready-to-attach files sit in `submission/`:

- `submission/report.pdf` (6 pages, embedded figures, ~800 KB)
- `submission/report.docx` (same content, Word-editable, ~700 KB)

Most reviewers prefer PDF for a final read. DOCX is there as a backup if the Google Form asks for an editable document.

The markdown source is `submission/report_full.md` if you ever want to tweak something and re-render.

## What to paste into the Google Form

Fill the form with these values (replace the GitHub username placeholder with yours).

| Field on the form          | What to put                                                                                              |
| -------------------------- | -------------------------------------------------------------------------------------------------------- |
| Name                       | Kartik Shirode                                                                                           |
| Email                      | (your email)                                                                                             |
| Resume                     | Upload PDF or paste your Google Drive link                                                               |
| GitHub repo                | `https://github.com/<your-username>/trader-sentiment-primetrade`                                         |
| Notebook (Colab) link      | `https://colab.research.google.com/github/<your-username>/trader-sentiment-primetrade/blob/main/notebooks/analysis.ipynb` |
| Written report             | Attach `submission/report.pdf` (or `submission/report.docx`)                                             |
| Short summary (if asked)   | See "Short summary" block below                                                                          |

### Short summary (paste into "summary" or "key findings" type fields)

```
Two years of Hyperliquid trades (211,224 rows) joined to the Bitcoin
Fear and Greed Index. Headline finding: Extreme Greed is the strongest
regime by every profitability metric (avg PnL $67.89, win rate 89.2 %,
profit factor 11.0, ROI 2.18 %), while plain Greed posts the lowest
Sharpe (3.41) and the worst drawdown in the dataset ($-419k). Long
share drops from 51.1 % in Extreme Fear to 44.9 % in Extreme Greed
(chi-square p < 1e-68), so the cohort runs a contrarian short bias
into overheated markets. Twenty-eight traders qualify for a Fear-vs-
Greed contrarian comparison; some show 50-point win-rate gaps between
regimes, which means two distinct sub-strategies are visible inside
the same population.

Stack: Python, pandas, numpy, matplotlib, seaborn, scipy. Code is
modular under src/ with unit tests under tests/, full notebook
under notebooks/, report under outputs/report.md plus the PDF/DOCX
versions in submission/.
```

## Pre-flight checks

Run these before submitting:

```powershell
# 1. Notebook actually re-executes from scratch
python build_notebook.py --force
jupyter nbconvert --to notebook --execute notebooks/analysis.ipynb --output analysis.ipynb --ExecutePreprocessor.timeout=600

# 2. Unit tests pass
python tests/test_metrics.py

# 3. No banned characters anywhere
git grep -P "[–—]" -- "*.md" "*.py" "*.txt" || echo "clean"

# 4. Submission artifacts present
ls submission/
```

Expected output of the last command:

```
analysis_colab.ipynb
build_colab_notebook.py
coin_regime_heatmap.png
contrarian_scatter.png
cumulative_pnl_by_regime.png
metrics_by_regime.png
pnl_box_by_regime.png
report.docx
report.pdf
report_full.md
sentiment_timeline.png
trades_eda.png
```

## If the form wants a single ZIP

A clean ZIP of everything Primetrade would need to evaluate the work offline:

```powershell
Compress-Archive -Path README.md, src, notebooks, outputs, tests, requirements.txt, submission\report.pdf, submission\report.docx -DestinationPath submission\primetrade_kartik_shirode.zip -Force
```

The ZIP excludes `data/raw/*.csv` (those are 47 MB, the notebook downloads them on demand). It also excludes `.git/` since you only need the source files.

## Contact for the form (from the original brief)

- Submission channel: Google Form (link shared by Primetrade Hiring)
- Hiring contact: Sonika, Primetrade.ai Hiring Team
- Notification window: shortlisted candidates notified by Saturday after submission
