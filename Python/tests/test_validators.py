"""Tests for bot.validators."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


def test_symbol_uppercases():
    assert validate_symbol("btcusdt") == "BTCUSDT"
    assert validate_symbol(" ethusdt ") == "ETHUSDT"


def test_symbol_rejects_invalid():
    for bad in ["", "BTC USDT", "BTC-USDT", "btc!", "ab", "x" * 25]:
        with pytest.raises(ValidationError):
            validate_symbol(bad)


def test_side_accepts_buy_sell_any_case():
    assert validate_side("buy") == "BUY"
    assert validate_side("SELL") == "SELL"
    assert validate_side(" Buy ") == "BUY"


def test_side_rejects_other():
    for bad in ["", "long", "short", "BUYY"]:
        with pytest.raises(ValidationError):
            validate_side(bad)


def test_order_type_accepts_three_types():
    assert validate_order_type("market") == "MARKET"
    assert validate_order_type("LIMIT") == "LIMIT"
    assert validate_order_type("stop_limit") == "STOP_LIMIT"
    assert validate_order_type("STOP-LIMIT") == "STOP_LIMIT"


def test_order_type_rejects_other():
    for bad in ["", "stop", "oco", "twap"]:
        with pytest.raises(ValidationError):
            validate_order_type(bad)


def test_quantity_accepts_positive_numbers():
    assert validate_quantity(0.001) == 0.001
    assert validate_quantity("1.5") == 1.5


def test_quantity_rejects_invalid():
    for bad in [0, -1, "nan", "abc", None, float("inf")]:
        with pytest.raises(ValidationError):
            validate_quantity(bad)


def test_price_required():
    assert validate_price(75000.0, required=True) == 75000.0
    with pytest.raises(ValidationError):
        validate_price(None, required=True)
    with pytest.raises(ValidationError):
        validate_price("", required=True)


def test_price_optional_allows_none():
    assert validate_price(None, required=False) is None
    assert validate_price("", required=False) is None
    assert validate_price(50000.0, required=False) == 50000.0


def test_price_rejects_non_positive():
    with pytest.raises(ValidationError):
        validate_price(0, required=True)
    with pytest.raises(ValidationError):
        validate_price(-5, required=True)
