"""Process startup script to alias httpx to httpx2 during pytest test runs."""

from __future__ import annotations

import os
import sys

# Only run alias_httpx() if pytest is running
if any("pytest" in arg for arg in sys.argv) or "PYTEST_CURRENT_TEST" in os.environ:
    import httpx2 as httpx

    if "httpx" not in sys.modules:
        httpx.alias_httpx()
