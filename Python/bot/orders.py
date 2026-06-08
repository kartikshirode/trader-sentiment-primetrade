"""Order-placement entry points used by the CLI and tests."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from .validators import (
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

log = logging.getLogger("binance_bot.orders")


class _ClientLike(Protocol):
    def place_order(self, **kwargs: Any) -> dict[str, Any]: ...


def place_market(client: _ClientLike, symbol: str, side: str, quantity) -> dict[str, Any]:
    sym = validate_symbol(symbol)
    s = validate_side(side)
    qty = validate_quantity(quantity)
    log.info("market order request: symbol=%s side=%s qty=%s", sym, s, qty)
    return client.place_order(symbol=sym, side=s, order_type="MARKET", quantity=qty)


def place_limit(
    client: _ClientLike, symbol: str, side: str, quantity, price
) -> dict[str, Any]:
    sym = validate_symbol(symbol)
    s = validate_side(side)
    qty = validate_quantity(quantity)
    p = validate_price(price, required=True, label="price")
    log.info("limit order request: symbol=%s side=%s qty=%s price=%s", sym, s, qty, p)
    return client.place_order(
        symbol=sym, side=s, order_type="LIMIT", quantity=qty, price=p
    )


def place_stop_limit(
    client: _ClientLike,
    symbol: str,
    side: str,
    quantity,
    stop_price,
    limit_price,
) -> dict[str, Any]:
    sym = validate_symbol(symbol)
    s = validate_side(side)
    qty = validate_quantity(quantity)
    sp = validate_price(stop_price, required=True, label="stop-price")
    lp = validate_price(limit_price, required=True, label="price")
    log.info(
        "stop-limit order request: symbol=%s side=%s qty=%s stop=%s limit=%s",
        sym, s, qty, sp, lp,
    )
    return client.place_order(
        symbol=sym, side=s, order_type="STOP_LIMIT",
        quantity=qty, price=lp, stop_price=sp,
    )
