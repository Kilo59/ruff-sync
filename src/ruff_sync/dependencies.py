"""Utilities for handling optional dependencies and lazy loading."""

from __future__ import annotations

import importlib
import importlib.util
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

__all__: Final[list[str]] = ["DependencyError", "is_installed", "require_dependency"]


class DependencyError(Exception):
    """Raised when a required optional dependency is missing or broken."""


def is_installed(package_name: str) -> bool:
    """Check if a package is installed without importing it.

    Args:
        package_name: The name of the package to check.

    Returns:
        True if the package is available, False otherwise.
    """
    return importlib.util.find_spec(package_name) is not None


def require_dependency(
    package_name: str,
    extra_name: str,
    *,
    _is_installed: Callable[[str], bool] = is_installed,
    _import_module: Callable[[str], Any] = importlib.import_module,
) -> None:
    """Ensure a dependency is installed and importable, or raise DependencyError.

    Args:
        package_name: The name of the required package.
        extra_name: The name of the ruff-sync extra that provides this package.
        _is_installed: Internal use only for testing. Function to check if a package is installed.
        _import_module: Internal use only for testing. Function to import a module.

    Raises:
        DependencyError: If the package is not installed or raises an error during import.
    """
    msg = (
        f"The '{package_name}' package is required for this feature. "
        f"Install it with: pip install 'ruff-sync[{extra_name}]'"
    )

    # 1. Fast check (dry) to see if it exists at all
    if not _is_installed(package_name):
        raise DependencyError(msg)

    # 2. Wet check (real import) to ensure it's functional
    try:
        _import_module(package_name)
    except (ImportError, ModuleNotFoundError) as e:
        # If it failed here, it's installed but BROKEN (e.g. missing sub-dependencies)
        raise DependencyError(msg) from e
