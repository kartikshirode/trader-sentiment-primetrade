"""Tests for src.config."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Config, ConfigError, load_config


def _write_yaml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "cfg.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_valid_config(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, 'seed: 42\nwindow: 5\nversion: "v1"\n')
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.seed == 42
    assert cfg.window == 5
    assert cfg.version == "v1"


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config file not found"):
        load_config(tmp_path / "nope.yaml")


def test_missing_key(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, 'seed: 42\nwindow: 5\n')
    with pytest.raises(ConfigError, match="missing required config key: version"):
        load_config(p)


def test_wrong_type(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, 'seed: "forty-two"\nwindow: 5\nversion: "v1"\n')
    with pytest.raises(ConfigError, match="seed must be int"):
        load_config(p)


def test_invalid_window(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, 'seed: 1\nwindow: 0\nversion: "v1"\n')
    with pytest.raises(ConfigError, match="window must be >= 1"):
        load_config(p)


def test_bool_rejected_as_int(tmp_path: Path) -> None:
    # YAML true would otherwise sneak through as int because bool is a subclass.
    p = _write_yaml(tmp_path, 'seed: true\nwindow: 5\nversion: "v1"\n')
    with pytest.raises(ConfigError, match="seed must be int"):
        load_config(p)


def test_malformed_yaml(tmp_path: Path) -> None:
    p = _write_yaml(tmp_path, "seed: 1\nwindow: [unterminated")
    with pytest.raises(ConfigError, match="failed to parse YAML"):
        load_config(p)
