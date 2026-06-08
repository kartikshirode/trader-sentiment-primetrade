"""Wrapper around python-binance for Binance Futures Testnet (USDT-M)."""
from __future__ import annotations

import logging
from typing import Any

try:
    from binance.client import Client
    from binance.enums import (
        FUTURE_ORDER_TYPE_LIMIT,
        FUTURE_ORDER_TYPE_MARKET,
        FUTURE_ORDER_TYPE_STOP,
        SIDE_BUY,
        SIDE_SELL,
        TIME_IN_FORCE_GTC,
    )
    from binance.exceptions import BinanceAPIException, BinanceRequestException
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "python-binance is required. Install with: pip install python-binance"
    ) from exc

log = logging.getLogger("binance_bot.client")


class OrderError(RuntimeError):
    """Raised when the Binance API returns an error or the network fails."""

    def __init__(self, message: str, code: int | None = None, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


_SIDE_MAP = {"BUY": SIDE_BUY, "SELL": SIDE_SELL}
_TYPE_MAP = {
    "MARKET": FUTURE_ORDER_TYPE_MARKET,
    "LIMIT": FUTURE_ORDER_TYPE_LIMIT,
    "STOP_LIMIT": FUTURE_ORDER_TYPE_STOP,  # Binance Futures uses STOP for stop-limit
}


class BinanceFuturesClient:
    """Thin wrapper that always talks to the Binance Futures Testnet."""

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise OrderError("api_key and api_secret are required for live testnet calls")
        # testnet=True is hardcoded so this client cannot ever hit live markets.
        self._client = Client(api_key, api_secret, testnet=True)

    def get_account_balance(self) -> list[dict]:
        """Return the futures account balances list (smoke-test connectivity)."""
        try:
            return self._client.futures_account_balance()
        except (BinanceAPIException, BinanceRequestException) as exc:
            raise self._wrap(exc) from exc

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_price: float | None = None,
        time_in_force: str = TIME_IN_FORCE_GTC,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": _SIDE_MAP[side],
            "type": _TYPE_MAP[order_type],
            "quantity": quantity,
        }
        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force
        elif order_type == "STOP_LIMIT":
            params["price"] = price
            params["stopPrice"] = stop_price
            params["timeInForce"] = time_in_force

        log.info("placing order: %s", {k: v for k, v in params.items() if k != "timestamp"})
        try:
            response = self._client.futures_create_order(**params)
        except (BinanceAPIException, BinanceRequestException) as exc:
            raise self._wrap(exc) from exc
        log.info("response orderId=%s status=%s", response.get("orderId"), response.get("status"))
        return response

    @staticmethod
    def _wrap(exc) -> OrderError:
        code = getattr(exc, "code", None)
        status_code = getattr(exc, "status_code", None)
        msg = str(exc) or exc.__class__.__name__
        return OrderError(msg, code=code, status_code=status_code)
