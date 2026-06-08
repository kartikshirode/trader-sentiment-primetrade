"""Tests for bot.orders using the DryRunClient (no network)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bot.dry_run import DryRunClient
from bot.orders import place_limit, place_market, place_stop_limit
from bot.validators import ValidationError


def test_market_order_returns_filled():
    client = DryRunClient()
    resp = place_market(client, "btcusdt", "buy", 0.001)
    assert resp["symbol"] == "BTCUSDT"
    assert resp["side"] == "BUY"
    assert resp["type"] == "MARKET"
    assert resp["status"] == "FILLED"
    assert resp["dryRun"] is True
    assert "orderId" in resp


def test_limit_order_returns_new():
    client = DryRunClient()
    resp = place_limit(client, "BTCUSDT", "SELL", 0.002, 75000.0)
    assert resp["status"] == "NEW"
    assert resp["type"] == "LIMIT"
    assert float(resp["price"]) == 75000.0


def test_stop_limit_includes_stop_price():
    client = DryRunClient()
    resp = place_stop_limit(client, "BTCUSDT", "BUY", 0.001, 65000.0, 64900.0)
    assert resp["type"] == "STOP_LIMIT"
    assert float(resp["stopPrice"]) == 65000.0
    assert float(resp["price"]) == 64900.0


def test_limit_requires_price():
    client = DryRunClient()
    with pytest.raises(ValidationError, match="price is required"):
        place_limit(client, "BTCUSDT", "BUY", 0.001, None)


def test_stop_limit_requires_both_prices():
    client = DryRunClient()
    with pytest.raises(ValidationError):
        place_stop_limit(client, "BTCUSDT", "BUY", 0.001, None, 64900.0)
    with pytest.raises(ValidationError):
        place_stop_limit(client, "BTCUSDT", "BUY", 0.001, 65000.0, None)


def test_market_rejects_bad_symbol():
    client = DryRunClient()
    with pytest.raises(ValidationError):
        place_market(client, "BTC-USDT", "BUY", 0.001)


def test_market_rejects_negative_qty():
    client = DryRunClient()
    with pytest.raises(ValidationError):
        place_market(client, "BTCUSDT", "BUY", -0.001)


def test_order_ids_are_monotonic():
    client = DryRunClient()
    r1 = place_market(client, "BTCUSDT", "BUY", 0.001)
    r2 = place_market(client, "BTCUSDT", "BUY", 0.001)
    assert r2["orderId"] > r1["orderId"]
