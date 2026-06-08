# End-to-end run for the DS pipeline on Windows PowerShell.
# Downloads raw data, regenerates the three notebooks, executes them,
# then runs pytest. Stops on the first failure.

$ErrorActionPreference = "Stop"

Write-Host "[1/5] downloading raw data"
python -c "from src.data_loader import download_raw; download_raw()"

Write-Host "[2/5] building notebooks"
python build_notebooks.py

Write-Host "[3/5] executing notebooks"
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb --output 01_eda.ipynb --ExecutePreprocessor.timeout=600
jupyter nbconvert --to notebook --execute notebooks/02_modeling.ipynb --output 02_modeling.ipynb --ExecutePreprocessor.timeout=600
jupyter nbconvert --to notebook --execute notebooks/03_backtest.ipynb --output 03_backtest.ipynb --ExecutePreprocessor.timeout=600

Write-Host "[4/5] running pytest"
python -m pytest -q

Write-Host "[5/5] done. Now run: streamlit run app/streamlit_app.py"
