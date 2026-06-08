# MLOps Task 0 (Primetrade.ai) Design

Date: 2026-06-08
Status: approved by user
Project root: `MLOP/`

## Context

Primetrade.ai's ML Engineering internship Task 0 is a 60-minute build that has to demonstrate three things end to end: reproducibility (config + seed), observability (logs + machine-readable metrics), and deployment readiness (one-command Docker run). The auto-fail bar is explicit (Docker must build, metrics.json must always be written, no hardcoded paths, deterministic outputs), so the design optimises for hitting every rubric line first and adding lightweight quality signals (pytest, type hints, module split) on top.

Scope chosen with the user: "Solid" tier, not minimum-viable and not gold-plated. No GitHub Actions, no multi-stage Docker, no pre-commit. The build should still feel senior.

Dataset is already pulled and cleaned at `MLOP/data.csv` (10,000 rows of BTC 1-min OHLCV from 2024-01-01 to 2024-01-07, zero nulls, all numeric except the timestamp).

## File layout

```
MLOP/
  run.py                   # CLI entry point, type-hinted, orchestrator only
  src/
    __init__.py            # public re-exports
    config.py              # YAML loader + dataclass validator
    pipeline.py            # load_data + compute_signal
    metrics.py             # write_success / write_error
    logging_setup.py       # setup_logger factory
  tests/
    __init__.py
    test_config.py
    test_pipeline.py
    test_metrics.py
  config.yaml              # seed: 42, window: 5, version: "v1"
  data.csv                 # 10k-row OHLCV (already downloaded)
  requirements.txt         # pandas, pyyaml; pytest in a dev section
  Dockerfile               # python:3.9-slim, COPYs data + config, CMD runs CLI
  .dockerignore
  README.md
  metrics.json             # sample successful output, committed
  run.log                  # sample log from a successful run, committed
```

## Module responsibilities

### `src/config.py`

- `Config` dataclass with `seed: int`, `window: int`, `version: str`.
- `load_config(path: Path) -> Config` parses YAML, validates required keys, validates types, raises `ConfigError` (custom exception subclassing `ValueError`) on any failure with a clear message.
- Sets `numpy.random.seed(config.seed)` as a side effect of `load_config` so callers do not have to remember.

### `src/pipeline.py`

- `load_data(path: Path) -> pandas.DataFrame`. Handles missing file (FileNotFoundError), empty file (raises `DataError`), invalid CSV (catches `pandas.errors.ParserError`, re-raises as `DataError`), missing `close` column (raises `DataError`). Custom `DataError` subclasses `ValueError`.
- `compute_signal(df: pandas.DataFrame, window: int) -> pandas.DataFrame`. Adds two columns: `rolling_mean` and `signal`. Decision: rolling mean for the first `window - 1` rows is NaN, and those rows get `signal = 0` (binary contract per spec, so NaN is not allowed in the output). Documented in the module docstring and the README.

### `src/metrics.py`

- `write_success(path, version, rows_processed, signal_rate, latency_ms, seed)` writes the success-shape JSON with exactly the 7 keys from the spec: `version, rows_processed, metric, value, latency_ms, seed, status`.
- `write_error(path, version, error_message)` writes the error-shape JSON: `version, status, error_message`.
- Both write atomically (write to `path.with_suffix('.tmp')`, then `os.replace`) so a crash mid-write cannot leave a half-formed file.

### `src/logging_setup.py`

- `setup_logger(log_file: Path, level: int = logging.INFO) -> logging.Logger`.
- Plain-text format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.
- Writes to both stdout and the file so docker logs and run.log stay in sync.
- Named logger `mlops` so all modules use `logging.getLogger('mlops.<module>')`.

### `run.py`

- argparse CLI with four required args (`--input`, `--config`, `--output`, `--log-file`).
- Wraps the whole pipeline in a top-level try/except. On failure: logs the exception, writes the error metrics file via `metrics.write_error`, exits 1. On success: writes the success metrics file, prints the metrics JSON to stdout (so Docker logs show it), exits 0.
- Times the full run with `time.perf_counter()` for `latency_ms`.

## CLI contract (verbatim from the spec)

```
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

No defaults that hardcode any path. All four flags required.

## Error handling matrix

| Failure                          | Caught where               | Exit code | Metrics status |
| -------------------------------- | -------------------------- | --------- | -------------- |
| Missing input file               | pipeline.load_data         | 1         | error          |
| Invalid CSV (parse fail)         | pipeline.load_data         | 1         | error          |
| Empty file                       | pipeline.load_data         | 1         | error          |
| Missing close column             | pipeline.load_data         | 1         | error          |
| Config file missing              | config.load_config         | 1         | error          |
| Config schema invalid            | config.load_config         | 1         | error          |
| Unexpected exception             | run.py outer try           | 1         | error          |
| Everything fine                  | n/a                        | 0         | success        |

## Docker

- Base: `python:3.9-slim` (matches the spec's suggested image, no surprises).
- Layer order: install OS deps if needed (none expected), COPY requirements.txt, pip install, COPY source + data + config last. This keeps the install layer cached when only source changes.
- WORKDIR `/app`.
- CMD: `["python", "run.py", "--input", "data.csv", "--config", "config.yaml", "--output", "metrics.json", "--log-file", "run.log"]`.
- Final container behaviour: produces metrics.json and run.log inside the container, prints the metrics JSON to stdout, exits 0 on success.
- `.dockerignore` excludes tests, __pycache__, the docs folder, and the .git tree to keep the image small.

## Tests (pytest)

- `tests/test_config.py`: valid YAML loads, missing key raises ConfigError, wrong-type value raises ConfigError, non-existent file raises ConfigError.
- `tests/test_pipeline.py`: hand-built 10-row fixture with known close prices. Rolling mean values match by hand. Signal flips correctly. First `window - 1` rows have signal = 0.
- `tests/test_metrics.py`: success shape has exactly the 7 spec keys with the right types. Error shape has the 3 spec keys. Both produce valid JSON parseable by `json.loads`.

Tests run with plain `pytest -q` from the `MLOP/` root.

## README

Five short sections:

1. What it does (one paragraph)
2. Local run command (exact CLI from the spec)
3. Docker build + run commands
4. Example metrics.json block (success and error)
5. How to run the tests (`pytest -q`)

Tone: human, no em dashes, no en dashes, no AI-template phrasing (per repo CLAUDE.md rule).

## Determinism guarantee

The pipeline is deterministic by construction (pandas rolling on a fixed input + a fixed window). The seed is still set in `load_config` so any future random component (e.g. a sampling step) inherits the determinism for free. Tests pin known input -> known output values to lock this in.

## Verification before commit

1. `python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log` produces metrics.json matching the spec format, non-empty run.log, exit code 0.
2. `python run.py --input nonexistent.csv ...` writes an error metrics.json, exit code 1.
3. `python run.py --input data.csv --config bad_config.yaml ...` writes an error metrics.json, exit code 1.
4. `pytest -q` all green.
5. `docker build -t mlops-task .` builds without errors (requires user to start Docker Desktop).
6. `docker run --rm mlops-task` reproduces metrics.json output identically to the local run.
7. `grep -P "[—–]"` returns nothing across README.md and *.py files.
8. Two consecutive local runs produce identical metrics.json (determinism check).

## Submission packaging

Same pattern as the DS submission: push `MLOP/` as a public GitHub repo, paste the repo URL into the Google Form, plus the README link if asked. Optional zip via PowerShell `Compress-Archive` if the form prefers a bundle.

## Out of scope (explicitly skipped)

- Multi-stage Dockerfile.
- GitHub Actions CI.
- Pre-commit hooks.
- JSON-structured logs.
- ruff or mypy configs.
- Any code beyond what the brief asks for.
