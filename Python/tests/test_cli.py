"""Tests for cli.py argparse + dispatch using dry-run mode."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cli


def _argv(tmp_path: Path, *extra: str) -> list[str]:
    log_path = tmp_path / "test_cli.log"
    return ["--dry-run", "--log-file", str(log_path), *extra]


def test_market_order_exits_zero(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path, "--symbol", "BTCUSDT", "--side", "BUY",
                        "--type", "MARKET", "--qty", "0.001"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "==== request ====" in out
    assert "==== response ====" in out
    assert "FILLED" in out


def test_limit_order_exits_zero(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path,
        "--symbol", "BTCUSDT", "--side", "SELL", "--type", "LIMIT",
        "--qty", "0.001", "--price", "75000",
    ))
    assert rc == 0
    out = capsys.readouterr().out
    assert "type:     LIMIT" in out
    assert "price:    75000.0" in out


def test_stop_limit_order_exits_zero(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path,
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "STOP_LIMIT",
        "--qty", "0.001", "--stop-price", "65000", "--price", "64900",
    ))
    assert rc == 0
    out = capsys.readouterr().out
    assert "type:     STOP_LIMIT" in out
    # Request block now uses "stop:" rather than "stopPrice:" for visual symmetry.
    assert "stop:     65000" in out


def test_limit_without_price_exits_one(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path,
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "LIMIT", "--qty", "0.001",
    ))
    assert rc == 1
    err = capsys.readouterr().err
    assert "price is required" in err


def test_stop_limit_missing_stop_price_exits_one(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path,
        "--symbol", "BTCUSDT", "--side", "BUY", "--type", "STOP_LIMIT",
        "--qty", "0.001", "--price", "64900",
    ))
    assert rc == 1
    err = capsys.readouterr().err
    assert "stop-price is required" in err


def test_bad_symbol_exits_one(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path, "--symbol", "BTC-USDT", "--side", "BUY",
                        "--type", "MARKET", "--qty", "0.001"))
    assert rc == 1


def test_argparse_rejects_unknown_type(tmp_path, capsys):
    # No argparse choices= constraint, so validator catches it and returns 1.
    rc = cli.main(_argv(tmp_path, "--symbol", "BTCUSDT", "--side", "BUY",
                        "--type", "OCO", "--qty", "0.001"))
    assert rc == 1
    err = capsys.readouterr().err
    assert "type must be one of" in err


def test_api_error_returns_two(tmp_path, capsys, monkeypatch):
    """When the client raises OrderError, the CLI must exit with code 2."""
    from bot.client import OrderError

    class _BoomClient:
        def place_order(self, **_kwargs):
            raise OrderError("boom", code=-2010, status_code=400)

        def get_account_balance(self):
            return []

    monkeypatch.setattr(cli, "DryRunClient", _BoomClient)
    rc = cli.main(_argv(tmp_path, "--symbol", "BTCUSDT", "--side", "BUY",
                        "--type", "MARKET", "--qty", "0.001"))
    assert rc == 2
    err = capsys.readouterr().err
    assert "api error:" in err


def test_check_balance_prints_usdt(tmp_path, capsys):
    rc = cli.main(_argv(tmp_path, "--check-balance",
                        "--symbol", "BTCUSDT", "--side", "BUY",
                        "--type", "MARKET", "--qty", "0.001"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "==== balance ====" in out
    assert "asset:     USDT" in out
    # DryRunClient hardcodes 15000 USDT available.
    assert "15000" in out


def test_lowercase_side_accepted(tmp_path, capsys):
    """Without argparse choices=, lowercase 'buy' should still be accepted."""
    rc = cli.main(_argv(tmp_path, "--symbol", "BTCUSDT", "--side", "buy",
                        "--type", "market", "--qty", "0.001"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "FILLED" in out
