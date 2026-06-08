"""Input validation for CLI args and order parameters."""
from __future__ import annotations

import math
import re


class ValidationError(ValueError):
    """Raised when CLI input or an order parameter is invalid."""


_VALID_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{4,20}$")


def validate_symbol(symbol: str) -> str:
    """Symbol is alphanumeric uppercase, 4 to 20 chars (e.g. BTCUSDT, ETHUSDT)."""
    if not isinstance(symbol, str) or not symbol:
        raise ValidationError("symbol is required")
    s = symbol.strip().upper()
    if not _SYMBOL_RE.match(s):
        raise ValidationError(f"symbol {symbol!r} is not a valid Binance pair (e.g. BTCUSDT)")
    return s


def validate_side(side: str) -> str:
    if not isinstance(side, str):
        raise ValidationError("side is required")
    s = side.strip().upper()
    if s not in {"BUY", "SELL"}:
        raise ValidationError(f"side must be BUY or SELL, got {side!r}")
    return s


def validate_order_type(order_type: str) -> str:
    if not isinstance(order_type, str):
        raise ValidationError("type is required")
    t = order_type.strip().upper().replace("-", "_")
    if t not in _VALID_TYPES:
        raise ValidationError(f"type must be one of {sorted(_VALID_TYPES)}, got {order_type!r}")
    return t


def validate_quantity(quantity) -> float:
    try:
        q = float(quantity)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"quantity must be numeric, got {quantity!r}") from exc
    if math.isnan(q) or math.isinf(q):
        raise ValidationError(f"quantity must be a finite number, got {quantity!r}")
    if q <= 0:
        raise ValidationError(f"quantity must be > 0, got {q}")
    return q


def validate_price(price, *, required: bool, label: str = "price") -> float | None:
    if price is None or price == "":
        if required:
            raise ValidationError(f"{label} is required for this order type")
        return None
    try:
        p = float(price)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} must be numeric, got {price!r}") from exc
    if math.isnan(p) or math.isinf(p):
        raise ValidationError(f"{label} must be a finite number, got {price!r}")
    if p <= 0:
        raise ValidationError(f"{label} must be > 0, got {p}")
    return p
