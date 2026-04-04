"""Tests for the dependencies module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ruff_sync.dependencies import is_installed, require_dependency


def test_is_installed_true() -> None:
    with patch("importlib.util.find_spec", return_value=True):
        assert is_installed("some_package") is True


def test_is_installed_false() -> None:
    with patch("importlib.util.find_spec", return_value=None):
        assert is_installed("nonexistent_package") is False


def test_require_dependency_success() -> None:
    with patch("ruff_sync.dependencies.is_installed", return_value=True):
        # Should not raise
        require_dependency("some_package", "some_extra")


def test_require_dependency_failure() -> None:
    with patch("ruff_sync.dependencies.is_installed", return_value=False):
        with pytest.raises(ImportError) as exc_info:
            require_dependency("textual", "tui")

        msg = str(exc_info.value)
        assert "textual" in msg
        assert "pip install 'ruff-sync[tui]'" in msg
