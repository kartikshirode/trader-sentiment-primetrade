"""Binance Futures Testnet trading bot for the Primetrade.ai Python intern task."""
try:
    from .client import BinanceFuturesClient, OrderError
except ImportError:
    # python-binance is optional. Without it, only --dry-run mode works.
    BinanceFuturesClient = None  # type: ignore[assignment,misc]
    OrderError = RuntimeError  # type: ignore[assignment,misc]
from .config import Credentials, load_credentials
from .dry_run import DryRunClient
from .logging_config import setup_logger
from .orders import place_limit, place_market, place_stop_limit
from .validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

__all__ = [
    "BinanceFuturesClient",
    "Credentials",
    "DryRunClient",
    "OrderError",
    "ValidationError",
    "load_credentials",
    "place_limit",
    "place_market",
    "place_stop_limit",
    "setup_logger",
    "validate_order_type",
    "validate_price",
    "validate_quantity",
    "validate_side",
    "validate_symbol",
]
