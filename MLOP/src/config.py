"""YAML config loading and validation for the MLOps Task 0 pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


class ConfigError(ValueError):
    """Raised when the config file is missing or has the wrong shape."""


@dataclass(frozen=True)
class Config:
    seed: int
    window: int
    version: str


_REQUIRED_TYPES: dict[str, type] = {
    "seed": int,
    "window": int,
    "version": str,
}


def _validate(raw: Any) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError(f"config root must be a mapping, got {type(raw).__name__}")
    for key, expected in _REQUIRED_TYPES.items():
        if key not in raw:
            raise ConfigError(f"missing required config key: {key}")
        value = raw[key]
        if not isinstance(value, expected) or isinstance(value, bool):
            raise ConfigError(
                f"config key {key} must be {expected.__name__}, got {type(value).__name__}"
            )
    if raw["window"] < 1:
        raise ConfigError(f"window must be >= 1, got {raw['window']}")
    return Config(seed=raw["seed"], window=raw["window"], version=raw["version"])


def load_config(path: Path) -> Config:
    """Parse, validate, and apply the YAML config at path.

    Sets numpy's RNG seed as a side effect so any downstream randomness inherits the determinism.
    Raises ConfigError on missing file, parse failure, or schema mismatch.
    """
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"config file not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigError(f"failed to parse YAML: {exc}") from exc
    cfg = _validate(raw)
    np.random.seed(cfg.seed)
    return cfg
