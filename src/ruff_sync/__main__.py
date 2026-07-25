"""Main entry point for ruff-sync when run as a module."""

from __future__ import annotations

import sys

import httpx2 as httpx

if "httpx" not in sys.modules:
    httpx.alias_httpx()

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
