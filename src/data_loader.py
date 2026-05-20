"""Download and load the two source datasets."""
from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
TRADES_FILE = RAW_DIR / "historical_trades.csv"
SENTIMENT_FILE = RAW_DIR / "fear_greed.csv"

TRADES_GDRIVE_ID = "1IAfLZwu6rJzyWKgBToqwSmmVYU6VbjVs"
SENTIMENT_GDRIVE_ID = "1PgQC0tO8XN-wqkNyghWc_-mnrYv_nhSf"


def download_raw(force: bool = False) -> None:
    """Pull both CSVs from Google Drive into data/raw/."""
    import gdown

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if force or not TRADES_FILE.exists():
        gdown.download(id=TRADES_GDRIVE_ID, output=str(TRADES_FILE), quiet=False)
        if not TRADES_FILE.exists() or TRADES_FILE.stat().st_size == 0:
            raise RuntimeError("Trades download failed. Check Google Drive permissions or try force=True.")
    if force or not SENTIMENT_FILE.exists():
        gdown.download(id=SENTIMENT_GDRIVE_ID, output=str(SENTIMENT_FILE), quiet=False)
        if not SENTIMENT_FILE.exists() or SENTIMENT_FILE.stat().st_size == 0:
            raise RuntimeError("Sentiment download failed. Check Google Drive permissions or try force=True.")


def load_trades() -> pd.DataFrame:
    """Load Hyperliquid trades and add a `date` column (UTC date from IST timestamp)."""
    df = pd.read_csv(TRADES_FILE)
    df.columns = [c.strip() for c in df.columns]
    df["ts"] = pd.to_datetime(df["Timestamp IST"], format="%d-%m-%Y %H:%M", errors="coerce")
    bad = df["ts"].isna().sum()
    if bad:
        print(f"dropped {bad} rows with unparseable Timestamp IST")
        df = df[df["ts"].notna()].copy()
    df["date"] = df["ts"].dt.date.astype("datetime64[ns]")
    df = df.rename(columns={
        "Closed PnL": "closed_pnl",
        "Size USD": "size_usd",
        "Size Tokens": "size_tokens",
        "Execution Price": "exec_price",
        "Start Position": "start_position",
        "Account": "account",
        "Coin": "coin",
        "Side": "side",
        "Direction": "direction",
        "Fee": "fee",
    })
    return df


def load_sentiment() -> pd.DataFrame:
    """Load the Bitcoin Fear & Greed Index file with a parsed date column."""
    df = pd.read_csv(SENTIMENT_FILE)
    df.columns = [c.strip() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="raise").dt.normalize()
    df = df.rename(columns={"value": "fg_value", "classification": "regime"})
    return df[["date", "fg_value", "regime"]]
