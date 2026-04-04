"""Utilities for handling optional dependencies and lazy loading."""

from __future__ import annotations

import importlib.util
from typing import Final

__all__: Final[list[str]] = ["is_installed", "require_dependency"]


def is_installed(package_name: str) -> bool:
    """Check if a package is installed without importing it.

    Args:
        package_name: The name of the package to check.

    Returns:
        True if the package is available, False otherwise.
    """
    return importlib.util.find_spec(package_name) is not None


def require_dependency(package_name: str, extra_name: str) -> None:
    """Ensure a dependency is installed, or raise a helpful ImportError.

    Args:
        package_name: The name of the required package.
        extra_name: The name of the ruff-sync extra that provides this package.

    Raises:
        ImportError: If the package is not installed.
    """
    if not is_installed(package_name):
        msg = (
            f"The '{package_name}' package is required for this feature. "
            f"Install it with: pip install 'ruff-sync[{extra_name}]'"
        )
        raise ImportError(msg)
