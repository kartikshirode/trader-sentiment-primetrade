"""Binance Futures Testnet trading bot CLI entry point."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from bot.client import BinanceFuturesClient, OrderError
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
    p.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    p.add_argument("--type", required=True, dest="order_type",
                   choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit", "STOP-LIMIT", "stop-limit"])
    p.add_argument("--qty", required=True, type=float, help="order quantity")
    p.add_argument("--price", type=float, default=None,
                   help="limit price (required for LIMIT and STOP_LIMIT)")
    p.add_argument("--stop-price", type=float, default=None,
                   help="stop trigger price (required for STOP_LIMIT)")
    p.add_argument("--log-file", type=Path, default=DEFAULT_LOG,
                   help="path for the run log (default: logs/run.log)")
    p.add_argument("--dry-run", action="store_true",
                   help="bypass the real testnet and use the offline canned client")
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
        print(f"stopPrice: {args.stop_price}")


def _print_response(resp: dict) -> None:
    print("==== response ====")
    keys = ["orderId", "symbol", "side", "type", "status", "origQty", "executedQty", "avgPrice", "price", "stopPrice", "dryRun"]
    for k in keys:
        if k in resp and resp[k] not in (None, "", "0.00"):
            print(f"{k}: {resp[k]}")


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

    _print_request(args, order_type)

    creds = load_credentials(force_dry_run=args.dry_run)
    if creds.is_dry_run:
        logger.info("using DryRunClient (no network)")
        client = DryRunClient()
    else:
        logger.info("using live testnet BinanceFuturesClient")
        client = BinanceFuturesClient(creds.api_key, creds.api_secret)

    try:
        if order_type == "MARKET":
            resp = place_market(client, args.symbol, args.side, args.qty)
        elif order_type == "LIMIT":
            resp = place_limit(client, args.symbol, args.side, args.qty, args.price)
        else:
            resp = place_stop_limit(client, args.symbol, args.side, args.qty, args.stop_price, args.price)
    except ValidationError as exc:
        logger.error("validation: %s", exc)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OrderError as exc:
        logger.error("api error (code=%s status=%s): %s", exc.code, exc.status_code, exc)
        print(f"api error: {exc}", file=sys.stderr)
        return 2

    _print_response(resp)
    logger.info("cli end: success orderId=%s status=%s", resp.get("orderId"), resp.get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
