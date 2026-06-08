"""Binance Futures Testnet trading bot CLI entry point."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from bot import BinanceFuturesClient, OrderError
from bot.config import load_credentials
from bot.dry_run import DryRunClient
from bot.logging_config import setup_logger
from bot.orders import place_limit, place_market, place_stop_limit
from bot.validators import ValidationError, validate_order_type

DEFAULT_LOG = Path("logs") / "run.log"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Place Market / Limit / Stop-Limit orders on Binance Futures Testnet",
    )
    p.add_argument("--symbol", required=True, help="trading pair e.g. BTCUSDT")
    # No choices= here on purpose. The validators normalise case and hyphens
    # and surface a friendly error rather than argparse's generic complaint.
    p.add_argument("--side", required=True, help="BUY or SELL (case-insensitive)")
    p.add_argument("--type", required=True, dest="order_type",
                   help="MARKET, LIMIT, or STOP_LIMIT (case-insensitive, hyphen ok)")
    p.add_argument("--qty", required=True, type=float, help="order quantity")
    p.add_argument("--price", type=float, default=None,
                   help="limit price (required for LIMIT and STOP_LIMIT)")
    p.add_argument("--stop-price", type=float, default=None,
                   help="stop trigger price (required for STOP_LIMIT)")
    p.add_argument("--log-file", type=Path, default=DEFAULT_LOG,
                   help="path for the run log (default: logs/run.log)")
    p.add_argument("--dry-run", action="store_true",
                   help="bypass the real testnet and use the offline canned client")
    p.add_argument("--check-balance", action="store_true",
                   help="fetch USDT balance and exit (fastest way to test credentials)")
    return p.parse_args(argv)


def _print_request(args: argparse.Namespace, order_type: str) -> None:
    print("==== request ====")
    print(f"symbol:   {args.symbol.upper()}")
    print(f"side:     {args.side.upper()}")
    print(f"type:     {order_type}")
    print(f"quantity: {args.qty}")
    if order_type in {"LIMIT", "STOP_LIMIT"}:
        print(f"price:    {args.price}")
    if order_type == "STOP_LIMIT":
        print(f"stop:     {args.stop_price}")


def _is_zero_or_empty(value) -> bool:
    """Return True if value should be skipped from the response print block."""
    if value is None or value == "":
        return True
    try:
        return float(value) == 0
    except (TypeError, ValueError):
        return False


def _print_response(resp: dict) -> None:
    print("==== response ====")
    keys = ["orderId", "symbol", "side", "type", "status", "origQty",
            "executedQty", "avgPrice", "price", "stopPrice", "dryRun"]
    for k in keys:
        if k in resp and not _is_zero_or_empty(resp[k]):
            print(f"{k}: {resp[k]}")


def _build_client(creds, logger: logging.Logger):
    """Construct the right client; raises OrderError / ImportError on failure."""
    if creds.is_dry_run:
        logger.info("using DryRunClient (no network)")
        return DryRunClient()
    if BinanceFuturesClient is None:
        raise ImportError(
            "install python-binance to use live testnet mode "
            "(pip install python-binance) or pass --dry-run"
        )
    logger.info("using live testnet BinanceFuturesClient")
    return BinanceFuturesClient(creds.api_key, creds.api_secret)


def _run_check_balance(client, logger: logging.Logger) -> int:
    """Print USDT balance from the account and return an exit code."""
    balances = client.get_account_balance()
    usdt = next((b for b in balances if b.get("asset") == "USDT"), None)
    if usdt is None:
        print("USDT balance not found in account", file=sys.stderr)
        logger.error("USDT balance missing from response: %s", balances)
        return 2
    available = usdt.get("availableBalance") or usdt.get("balance") or "0"
    print("==== balance ====")
    print(f"asset:     USDT")
    print(f"available: {available}")
    logger.info("balance check ok: USDT available=%s", available)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logger = setup_logger(args.log_file)
    logger.info("cli start: %s", " ".join(sys.argv[1:]))

    try:
        order_type = validate_order_type(args.order_type)
    except ValidationError as exc:
        logger.error("validation: %s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not args.check_balance:
        _print_request(args, order_type)

    creds = load_credentials(force_dry_run=args.dry_run)

    try:
        client = _build_client(creds, logger)
        if args.check_balance:
            return _run_check_balance(client, logger)
        if order_type == "MARKET":
            resp = place_market(client, args.symbol, args.side, args.qty)
        elif order_type == "LIMIT":
            resp = place_limit(client, args.symbol, args.side, args.qty, args.price)
        else:
            resp = place_stop_limit(client, args.symbol, args.side, args.qty,
                                    args.stop_price, args.price)
    except ValidationError as exc:
        logger.error("validation: %s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OrderError as exc:
        logger.error("api error (code=%s status=%s): %s",
                     getattr(exc, "code", None), getattr(exc, "status_code", None), exc)
        print(f"api error: {exc}", file=sys.stderr)
        return 2

    _print_response(resp)
    logger.info("cli end: success orderId=%s status=%s",
                resp.get("orderId"), resp.get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
