"""Offline client that returns canned Binance-shaped responses.

Used automatically when API credentials are missing, when DRY_RUN=1 is set,
or when --dry-run is passed on the CLI. No network calls. Deterministic except
for the order ID counter, which increments monotonically per process.
"""
from __future__ import annotations

import itertools
import logging
from typing import Any

log = logging.getLogger("binance_bot.dry_run")


class DryRunClient:
    """Stand-in for BinanceFuturesClient with the same public interface."""

    _order_id_counter = itertools.count(999000001)

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def get_account_balance(self) -> list[dict]:
        return [
            {"asset": "USDT", "balance": "15000.00000000", "availableBalance": "15000.00000000"},
            {"asset": "BNB", "balance": "0.00000000", "availableBalance": "0.00000000"},
        ]

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        order_id = next(self._order_id_counter)
        # Market orders fill immediately at a stubbed price; limit/stop-limit stay open.
        if order_type == "MARKET":
            avg_price = "67234.50"
            status = "FILLED"
            executed_qty = f"{quantity:.6f}"
        else:
            avg_price = "0.00"
            status = "NEW"
            executed_qty = "0.000000"

        response = {
            "orderId": order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "status": status,
            "origQty": f"{quantity:.6f}",
            "executedQty": executed_qty,
            "avgPrice": avg_price,
            "price": f"{price:.2f}" if price is not None else "0.00",
            "stopPrice": f"{stop_price:.2f}" if stop_price is not None else "0.00",
            "timeInForce": time_in_force,
            "dryRun": True,
        }
        log.info(
            "dry-run order placed: orderId=%s symbol=%s side=%s type=%s qty=%s",
            order_id, symbol, side, order_type, quantity,
        )
        return response
