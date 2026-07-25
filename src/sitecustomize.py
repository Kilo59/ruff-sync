"""Process startup script to alias httpx to httpx2 during pytest test runs.

PACKAGING INTENT:
This file must NEVER be included in built wheels (.whl) or release distributions.
It lives outside `src/ruff_sync/` and is excluded from packaging by Hatchling
(`packages = ["src/ruff_sync"]`). If the build backend or target configuration is
ever changed in `pyproject.toml`, ensure this file remains strictly excluded.
"""

from __future__ import annotations

import os
import sys

# Only run alias_httpx() if pytest is running
if any("pytest" in arg for arg in sys.argv) or "PYTEST_CURRENT_TEST" in os.environ:
    import httpx2 as httpx

    if "httpx" not in sys.modules:
        httpx.alias_httpx()
