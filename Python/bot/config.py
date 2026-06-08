"""Load Binance Futures Testnet credentials from .env or env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore


@dataclass(frozen=True)
class Credentials:
    api_key: str
    api_secret: str
    is_dry_run: bool


def _load_env() -> None:
    """Load .env from the project root if python-dotenv is available."""
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def load_credentials(force_dry_run: bool = False) -> Credentials:
    """Return creds + dry-run flag.

    Dry run if force_dry_run, or DRY_RUN env is truthy, or either key is missing.
    Real testnet calls happen only when both keys are present and dry_run is False.
    """
    _load_env()
    api_key = (os.environ.get("BINANCE_TESTNET_API_KEY") or "").strip()
    api_secret = (os.environ.get("BINANCE_TESTNET_API_SECRET") or "").strip()
    env_dry = os.environ.get("DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
    is_dry_run = force_dry_run or env_dry or not (api_key and api_secret)
    return Credentials(api_key=api_key, api_secret=api_secret, is_dry_run=is_dry_run)
