"""Utilities for handling optional dependencies and lazy loading."""

from __future__ import annotations

import importlib
import importlib.util
import sys
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
    """Ensure a dependency is installed and importable, or exit with a helpful message.

    Args:
        package_name: The name of the required package.
        extra_name: The name of the ruff-sync extra that provides this package.

    Raises:
        SystemExit: If the package is not installed or raises an error during import.
    """
    msg = (
        f"The '{package_name}' package is required for this feature. "
        f"Install it with: pip install 'ruff-sync[{extra_name}]'"
    )

    # 1. Fast check (dry) to see if it exists at all
    if not is_installed(package_name):
        print(f"❌ {msg}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    # 2. Wet check (real import) to ensure it's functional
    try:
        importlib.import_module(package_name)
    except (ImportError, ModuleNotFoundError):
        # If it failed here, it's installed but BROKEN (e.g. missing sub-dependencies)
        print(f"❌ {msg}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
