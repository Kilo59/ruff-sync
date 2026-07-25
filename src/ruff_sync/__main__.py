"""Main entry point for ruff-sync when run as a module."""

from __future__ import annotations

import contextlib
import sys

import httpx2 as httpx

with contextlib.suppress(RuntimeError):
    alias_func = getattr(httpx, "alias_httpx", None)
    if callable(alias_func):
        alias_func()

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
