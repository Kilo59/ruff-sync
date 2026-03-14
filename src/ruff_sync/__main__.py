"""Main entry point for ruff-sync when run as a module."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
