# Binance Futures Testnet Trading Bot

Primetrade.ai Python Developer intern assignment. CLI tool that places Market, Limit, and Stop-Limit orders on Binance Futures Testnet (USDT-M). Built with `python-binance`. Clean separation between API client, CLI, validation, and logging. Works offline in dry-run mode for tests and demos, or against the real testnet once API keys are configured.

## Quick start

```
pip install -r requirements.txt
cp .env.example .env       # then paste your testnet keys into .env
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

If no `.env` exists, the CLI runs in dry-run mode automatically (canned responses, no network).

## Getting Binance Futures Testnet API keys

1. Go to **`https://testnet.binancefuture.com`** (this is the Futures USDT-M testnet, NOT the Spot testnet).
2. Sign in with **GitHub** or **Google**. No registration form.
3. Scroll to the bottom of the dashboard and click **Generate** under "API Key".
4. Copy both the API Key and the API Secret immediately (secret shows only once).
5. When generating, leave **"Restrict access to trusted IPs only" UNCHECKED**.
6. Make sure **Reading + Futures + Trading** permissions are all enabled.
7. Paste the values into `.env`.

The testnet pre-funds your account with virtual USDT. Zero real money risk.

## Sample CLI invocations

```
# Market order (immediately fills at current price)
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Limit order (rests on the book until the price is hit)
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 75000

# Stop-Limit order (becomes a limit order once the stop price triggers)
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --qty 0.001 --stop-price 65000 --price 64900

# Force dry-run even when keys are present
python cli.py --dry-run --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Custom log file path
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 --log-file logs/my_run.log

# Quick credential smoke test (no order placed)
python cli.py --check-balance --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

The `--check-balance` flag hits the account balance endpoint and prints the USDT
available, then exits. It is the fastest way to confirm your keys are accepted
before placing any orders. It still needs the regular order args because
argparse requires them, but they are ignored when `--check-balance` is set.

## Output shape

```
==== request ====
symbol:   BTCUSDT
side:     BUY
type:     MARKET
quantity: 0.001
==== response ====
orderId: 999000001
symbol: BTCUSDT
side: BUY
type: MARKET
status: FILLED
origQty: 0.001000
executedQty: 0.001000
avgPrice: 67234.50
```

Exit codes: `0` on success, `1` on validation error, `2` on Binance API error.

## Folder layout

```
Python/
  bot/
    __init__.py
    client.py             python-binance wrapper, testnet=True hardcoded
    dry_run.py            canned-response client for offline testing
    orders.py             place_market / place_limit / place_stop_limit
    validators.py         symbol/side/qty/price validation
    config.py             loads credentials from .env or env vars
    logging_config.py     file + stderr logger factory
  tests/
    test_validators.py    10 tests on each validator
    test_orders.py        8 tests using DryRunClient
    test_cli.py           11 tests on argparse + exit codes
  logs/
    market_order_sample.log
    limit_order_sample.log
    stop_limit_order_sample.log
  cli.py                  argparse entry point
  .env                    gitignored, holds your keys
  .env.example            template
  requirements.txt
  README.md
```

## Tests

```
pytest -q
```

29 tests, runs in under a second. All use the `DryRunClient` so no network or API keys required.

## Sample logs

`logs/` contains three sample run logs that prove the bot executes cleanly end to end: one MARKET order, one LIMIT order, one STOP_LIMIT order. They were generated with `--dry-run` so they are reproducible without keys. Once you have working testnet credentials, re-run the same commands without `--dry-run` to overwrite them with real testnet logs.

## Design notes

- `testnet=True` is hardcoded in `BinanceFuturesClient`. There is no code path that hits the live Binance market.
- The dry-run client is the same interface as the real client, so tests cover the entire dispatch path without needing the network. Order IDs are monotonic per process for predictable logs.
- Logging goes to a file plus stderr. Stdout carries only the request/response print blocks so a caller can pipe stdout into `jq` or another parser cleanly.
- The Stop-Limit type maps to Binance Futures `STOP` order type with both `price` (limit) and `stopPrice` (trigger) set.

## Troubleshooting

| Symptom                                         | Likely cause |
| ----------------------------------------------- | ------------ |
| `APIError(code=-2015) Invalid API-key...`       | Keys from wrong testnet (Spot vs Futures), IP restriction enabled, or missing Futures permission. Run `python cli.py --check-balance ...` to confirm before placing real orders. The keys committed in any local `.env` left over from earlier dev returned `-2015` and should be regenerated from the testnet dashboard. |
| `APIError(code=-1021) Timestamp ahead`          | System clock drift; sync time |
| `APIError(code=-2019) Margin insufficient`      | Trying to place a position size larger than virtual balance covers |
| `APIError(code=-4164) Notional too small`       | Binance Futures has a minimum notional (`qty * price >= 100` USDT for BTCUSDT); raise `--qty` |
| Bot stays in dry-run mode despite `.env`        | Check that the file is at the project root and uses `BINANCE_TESTNET_API_KEY` and `BINANCE_TESTNET_API_SECRET` exact names |

## Submission

Push `Python/` as a public GitHub repo, paste URL into the Google Form. `.env.example` shows the reviewer where to paste their own testnet keys; the real `.env` stays gitignored. Sample logs in `logs/` are committed so the reviewer can see the bot ran cleanly without needing to provision keys themselves.
