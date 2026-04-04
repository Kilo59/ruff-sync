from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from ruff_sync import get_config
from ruff_sync.cli import LOGGER

if TYPE_CHECKING:
    import pathlib


@pytest.fixture
def clean_config_cache():
    """Ensure get_config cache is clear before and after each test."""
    # Ensure LOGGER can be captured by caplog
    original_propagate = LOGGER.propagate
    LOGGER.propagate = True
    get_config.cache_clear()
    yield
    get_config.cache_clear()
    LOGGER.propagate = original_propagate


def test_get_config_warns_on_unknown_key(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://github.com/org/repo"
unknown_key = "value"
"""
    )

    # We need to ensure the logger is set up to capture the warning
    # In ruff_sync.py, get_config is called before handlers are added in main()
    # But in tests, caplog should catch it if the level is right.

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration: unknown_key" in caplog.text
    assert "upstream" in config
    assert "unknown_key" not in config


def test_get_config_warns_on_command_key(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
command = "pull"
"""
    )

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration: command" in caplog.text
    assert "command" not in config


def test_get_config_passes_allowed_keys(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://github.com/org/repo"
exclude = ["lint.per-file-ignores"]
branch = "develop"
"""
    )

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration" not in caplog.text
    assert config["upstream"] == "https://github.com/org/repo"
    assert config["exclude"] == ["lint.per-file-ignores"]
    assert config["branch"] == "develop"


def test_get_config_key_normalization(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    """Verify that both dashed and legacy keys are normalized correctly."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
# Canonical dashed key
pre-commit-version-sync = true
# Legacy underscored key (alias)
pre_commit_sync = false
# Another legacy alias
pre-commit = true
# Canonical with dashes
output-format = "github"
"""
    )
    # Note: in a real TOML, the last value for the same normalized key WOULD win
    # because they all map to 'pre_commit_version_sync'.
    # But TOML itself doesn't allow duplicate keys if they have the same name.
    # Here they have different names in TOML but map to the same name in Python.

    config = get_config(tmp_path)

    # 'pre-commit-version-sync' -> 'pre_commit_version_sync'
    # 'pre_commit_sync' -> 'pre_commit_version_sync'
    # 'pre-commit' -> 'pre_commit_version_sync'
    # The last one in the file wins if they map to the same key.
    assert config["pre_commit_version_sync"] is True
    assert config["output_format"] == "github"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
