from __future__ import annotations

from typing import Any

import pytest

from ruff_sync.dependencies import DependencyError, is_installed, require_dependency


def test_is_installed_true() -> None:
    # 'sys' is always installed
    assert is_installed("sys") is True


def test_is_installed_false() -> None:
    assert is_installed("nonexistent_package_12345") is False


def test_require_dependency_success() -> None:
    # No error should be raised when both check and import succeed
    require_dependency(
        "some_package",
        "some_extra",
        _is_installed=lambda _: True,
        _import_module=lambda _: None,
    )


def test_require_dependency_not_installed() -> None:
    # Should raise DependencyError if not installed
    with pytest.raises(DependencyError) as exc_info:
        require_dependency(
            "textual",
            "tui",
            _is_installed=lambda _: False,
        )

    msg = str(exc_info.value)
    assert "textual" in msg
    assert "pip install 'ruff-sync[tui]'" in msg


def test_require_dependency_broken_import() -> None:
    # Should raise DependencyError if installed but import fails (broken)
    def broken_import(_name: str) -> Any:
        msg = "Something went wrong during import"
        raise ImportError(msg)

    with pytest.raises(DependencyError) as exc_info:
        require_dependency(
            "broken_pkg",
            "broken_extra",
            _is_installed=lambda _: True,
            _import_module=broken_import,
        )

    msg = str(exc_info.value)
    assert "broken_pkg" in msg
    assert "pip install 'ruff-sync[broken_extra]'" in msg
