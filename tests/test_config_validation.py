from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from ruff_sync import LOGGER, get_config

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


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
