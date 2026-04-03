"""Ruff sync package.

This package provides tools to synchronize ruff configuration across projects.
"""

from __future__ import annotations

from .cli import (
    Arguments,
    __version__,
    get_config,
    main,
)
from .constants import OutputFormat
from .core import (
    Config,
    FetchResult,
    RuffConfigFileName,
    check,
    fetch_upstream_config,
    get_ruff_config,
    get_ruff_tool_table,
    is_ruff_toml_file,
    merge_ruff_toml,
    pull,
    resolve_raw_url,
    to_git_url,
    toml_ruff_parse,
)
from .formatters import get_formatter

__all__ = [
    "Arguments",
    "Config",
    "FetchResult",
    "OutputFormat",
    "RuffConfigFileName",
    "__version__",
    "check",
    "fetch_upstream_config",
    "get_config",
    "get_formatter",
    "get_ruff_config",
    "get_ruff_tool_table",
    "is_ruff_toml_file",
    "main",
    "merge_ruff_toml",
    "pull",
    "resolve_raw_url",
    "to_git_url",
    "toml_ruff_parse",
]
