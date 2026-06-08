# Python Binance Futures Testnet Bot Design

Date: 2026-06-08
Status: approved by user
Project root: `Python/`

## Context

Primetrade.ai Python Developer Intern assignment. 60-minute scope. Build a CLI tool that places Market and Limit orders on Binance Futures Testnet (USDT-M) with clean separation between API client, CLI, validation, and logging. Bonus: add a third order type (Stop-Limit). Real testnet keys are in `.env` and confirmed valid (64-char each, prefixed U0Pq / ABRv). `.env` already gitignored.

Stack confirmed: `python-binance` (matches public reference submissions, mature wrapper, handles HMAC signing).

## File layout

```
Python/
  bot/
    __init__.py
    client.py             BinanceFuturesClient wrapper around python-binance, testnet=True
    dry_run.py            DryRunClient with canned responses for offline testing
    orders.py             place_market / place_limit / place_stop_limit dispatchers
    validators.py         symbol/side/qty/price validators with ValidationError
    config.py             load_credentials from .env or env vars; decides dry-run when missing
    logging_config.py     file + stdout logger factory (same shape as MLOps)
  tests/
    __init__.py
    test_validators.py    good + bad inputs per validator
    test_orders.py        dry-run client; verifies correct method called with correct args
    test_cli.py           argparse parsing + exit codes
  logs/                   sample run logs committed for the submission
  .env                    gitignored, holds real keys
  .env.example            template the reviewer can copy
  cli.py                  argparse entry point
  requirements.txt        python-binance, python-dotenv, pytest
  README.md
```

## Module responsibilities

### `bot/config.py`

- `Credentials` dataclass: `api_key: str`, `api_secret: str`, `is_dry_run: bool`.
- `load_credentials() -> Credentials`: loads `.env` via `python-dotenv`, then reads `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` from env. If either is missing OR if `DRY_RUN=1` is set, returns dry-run mode.

### `bot/client.py`

- `BinanceFuturesClient(api_key, api_secret)`: wraps `binance.client.Client(api_key, api_secret, testnet=True)`. The `testnet=True` is hardcoded and never configurable so no path leads to a live-market call.
- `place_order(symbol, side, type, quantity, price=None, stop_price=None, time_in_force='GTC')`: dispatches to `futures_create_order` with the right param set per type. Maps `BinanceAPIException` to a custom `OrderError(message, code, status_code)` with a clean string.
- `get_account_balance() -> dict`: thin pass-through for the README to demo connectivity.

### `bot/dry_run.py`

- `DryRunClient`: same interface as `BinanceFuturesClient` but returns canned dicts shaped like real Binance responses (`{"orderId": 999000+N, "symbol": "BTCUSDT", "status": "FILLED", "executedQty": "0.001", "avgPrice": "67234.50", ...}`). Order ID monotonically increases per call.
- Used automatically when `Credentials.is_dry_run` is true.

### `bot/orders.py`

Three small functions, each takes the client and returns the response dict:

- `place_market(client, symbol, side, quantity) -> dict`
- `place_limit(client, symbol, side, quantity, price) -> dict`
- `place_stop_limit(client, symbol, side, quantity, stop_price, limit_price) -> dict`

Each calls the validators first, then delegates to `client.place_order`. Logs the request + response.

### `bot/validators.py`

- `ValidationError(ValueError)` custom exception.
- `validate_symbol(symbol: str) -> str`: uppercase, alphanumeric, ends in USDT or similar quote.
- `validate_side(side: str) -> str`: must be "BUY" or "SELL" (case-insensitive, returned upper).
- `validate_order_type(t: str) -> str`: must be "MARKET", "LIMIT", or "STOP_LIMIT".
- `validate_quantity(qty: float) -> float`: positive, not NaN.
- `validate_price(price: float | None, required: bool) -> float | None`: if required, must be positive; if not required, may be None.

### `bot/logging_config.py`

- `setup_logger(log_file: Path) -> logging.Logger`: same pattern as MLOps. Plain text format, both stdout and file handlers, named logger `binance_bot`.

### `cli.py`

- argparse CLI with subcommand-free flag style:
  ```
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 75000
  python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.001 --stop-price 65000 --price 64900
  ```
- Required args: `--symbol`, `--side`, `--type`, `--qty`.
- Conditional args: `--price` required for LIMIT and STOP_LIMIT; `--stop-price` required for STOP_LIMIT.
- Optional: `--log-file` (default `logs/run.log`), `--dry-run` (force dry run even with keys present).
- Prints a clean request summary before placing, then the response after.
- Exit 0 on success, 1 on validation error, 2 on API error.

## CLI output shape

```
==== request ====
symbol:   BTCUSDT
side:     BUY
type:     MARKET
quantity: 0.001
==== response ====
orderId:    1234567890
status:     FILLED
executedQty: 0.001
avgPrice:   67234.50
```

## Tests (pytest)

- `test_validators.py`: each validator with happy path + at least one bad case raising ValidationError.
- `test_orders.py`: uses DryRunClient. Asserts each `place_*` function calls the client with the right arg dict and returns a dict with expected keys.
- `test_cli.py`: argparse parsing happy path and one error case (LIMIT without --price exits non-zero). Uses `runpy` or `subprocess` style invocation in dry-run mode so no network.

## Sample logs

Two committed log files in `logs/`:

- `market_order_sample.log` (one BUY MARKET BTCUSDT 0.001 against the real testnet)
- `limit_order_sample.log` (one SELL LIMIT BTCUSDT 0.001 at a price safely above market against the real testnet)

If the testnet keys work end-to-end during build, these are real run logs. If anything blocks, fall back to dry-run logs and note in README that they were generated with `DRY_RUN=1`.

## Determinism / Reproducibility

Not strictly applicable (orders hit a live testnet that can be rate-limited or partially fill). The dry-run path IS deterministic: canned responses, monotonic order IDs, same output every run for tests.

## Verification

1. `pytest -q` all green.
2. `python cli.py --dry-run --symbol BTCUSDT --side BUY --type MARKET --qty 0.001` succeeds, writes log.
3. `python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001` (with real keys) succeeds against testnet, writes log.
4. `python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 75000` succeeds, writes log.
5. `python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.001 --stop-price 65000 --price 64900` succeeds, writes log.
6. Invalid input (e.g. `--type LIMIT` without `--price`) exits non-zero with friendly error.
7. Em/en dash grep clean on README and code.
8. `.env` is NOT in git history. Verify with `git log --all --source -- Python/.env` (should be empty).

## Out of scope

- OCO, TWAP, Grid (deferred bonuses).
- Streamlit UI (deferred bonus).
- Position/balance dashboard.
- Websocket streaming.
- Custom retry loop with exponential backoff (python-binance has built-in basic retries).

## Submission packaging

Same pattern as MLOps and DS: push `Python/` as a public GitHub repo, paste URL into Google Form. `.env.example` shows the reviewer where to paste their own keys. Sample logs prove the bot ran end-to-end.
