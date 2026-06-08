"""Tests for cli.py argparse + dispatch using dry-run mode."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


def _argv(*extra: str) -> list[str]:
    return ["--dry-run", "--log-file", "logs/test_cli.log", *extra]


def test_market_order_exits_zero(capsys):
    rc = cli.main(_argv("--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--qty", "0.001"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "==== request ====" in out
    assert "==== response ====" in out
    assert "FILLED" in out


def test_limit_order_exits_zero(capsys):
    rc = cli.main(_argv(
        "--symbol", "BTCUSDT", "--side", "SELL", "--type", "LIMIT",
        "--qty", "0.001", "--price", "75000",
    ))
    assert rc == 0
    out = capsys.readouterr().out
    assert "type:     LIMIT" in out
    assert "price:    75000.0" in out


def test_stop_limit_order_exits_zero(capsys):
    rc = cli.main(_argv(
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "STOP_LIMIT",
        "--qty", "0.001", "--stop-price", "65000", "--price", "64900",
    ))
    assert rc == 0
    out = capsys.readouterr().out
    assert "type:     STOP_LIMIT" in out
    assert "stopPrice: 65000" in out


def test_limit_without_price_exits_one(capsys):
    rc = cli.main(_argv(
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "LIMIT", "--qty", "0.001",
    ))
    assert rc == 1
    err = capsys.readouterr().err
    assert "price is required" in err


def test_stop_limit_missing_stop_price_exits_one(capsys):
    rc = cli.main(_argv(
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "STOP_LIMIT",
        "--qty", "0.001", "--price", "64900",
    ))
    assert rc == 1
    err = capsys.readouterr().err
    assert "stop-price is required" in err


def test_bad_symbol_exits_one(capsys):
    rc = cli.main(_argv("--symbol", "BTC-USDT", "--side", "BUY", "--type", "MARKET", "--qty", "0.001"))
    assert rc == 1


def test_argparse_rejects_unknown_type():
    with pytest.raises(SystemExit):
        cli.main(_argv("--symbol", "BTCUSDT", "--side", "BUY", "--type", "OCO", "--qty", "0.001"))
