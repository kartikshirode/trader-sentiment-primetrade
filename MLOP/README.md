# MLOps Task 0 (Primetrade.ai)

Minimal batch job that loads YAML config, reads a 10,000-row BTC OHLCV file, computes a rolling mean on `close`, generates a binary signal where `close > rolling_mean`, and writes structured metrics plus a log file. Runs locally with one CLI command, runs in Docker with one `docker run`.

## Local run

```
pip install -r requirements.txt
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

All four flags are required (no hardcoded defaults). The program writes `metrics.json` and `run.log`, prints the final metrics JSON to stdout, and exits 0 on success or 1 on any handled error.

## Docker

```
docker build -t mlops-task .
docker run --rm mlops-task
```

The image bundles `data.csv` and `config.yaml`, so no flags are needed at runtime. The container prints the final metrics JSON to stdout and exits with the program's exit code.

## Example output

Successful run:

```json
{
  "version": "v1",
  "rows_processed": 10000,
  "metric": "signal_rate",
  "value": 0.4989,
  "latency_ms": 16,
  "seed": 42,
  "status": "success"
}
```

Error run (for example, missing input file):

```json
{
  "version": "v1",
  "status": "error",
  "error_message": "input file not found: nonexistent.csv"
}
```

Sample files committed to the repo: [metrics.json](metrics.json) and [run.log](run.log).

## Project layout

```
MLOP/
  run.py                   CLI orchestrator
  src/
    config.py              YAML loader + dataclass validator
    pipeline.py            load_data + compute_signal
    metrics.py             atomic write_success / write_error
    logging_setup.py       file + stdout logger factory
  tests/                   pytest suite (17 tests)
  config.yaml              seed 42, window 5, version v1
  data.csv                 10k-row BTC OHLCV input
  Dockerfile               python:3.9-slim, single-stage
  requirements.txt
  README.md
  metrics.json             sample success output
  run.log                  sample log
```

## Design choices worth a callout

- **Warm-up rows.** The rolling mean of the first `window - 1` rows is NaN. Those rows get `signal = 0` so the output is strictly binary as the spec requires. `signal_rate` is the mean across all `rows_processed`, including the zeros at the start.
- **Determinism.** `np.random.seed(seed)` is set inside `load_config` as a side effect. The pipeline itself has no randomness today, but any future sampling step inherits the seed for free. Two consecutive runs produce identical `metrics.json` minus the `latency_ms` field.
- **Atomic writes.** `metrics.py` writes to `metrics.json.tmp` then `os.replace`s into place so a crash mid-write cannot leave a half-formed JSON file. The metrics file always exists after the program finishes, success or failure.
- **Logging.** Plain-text format `YYYY-MM-DDTHH:MM:SS [LEVEL] mlops: message`, written to both the log file and stdout. The Docker logs match the run.log file.

## Tests

```
pytest -q
```

Covers config validation (valid, missing key, wrong type, malformed YAML, bool-as-int trap), pipeline behaviour (rolling mean + signal on a hand-built fixture, warm-up zero policy, immutability of input), and metrics file shape (success keys, error keys, atomic write).

## Submission

Push the `MLOP/` folder as a public GitHub repo, then paste the URL into the Google Form Primetrade sends. Optional: zip the folder with PowerShell `Compress-Archive` if the form prefers a bundle.
