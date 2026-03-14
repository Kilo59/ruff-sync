"""Ruff sync package.

This package provides tools to synchronize ruff configuration across projects.
"""

from __future__ import annotations

from .cli import (
    Arguments,
    Config,
    FetchResult,
    __version__,
    check,
    fetch_upstream_config,
    get_config,
    get_ruff_config,
    get_ruff_tool_table,
    is_ruff_toml_file,
    main,
    merge_ruff_toml,
    pull,
    resolve_raw_url,
    to_git_url,
    toml_ruff_parse,
)

__all__ = [
    "Arguments",
    "Config",
    "FetchResult",
    "__version__",
    "check",
    "fetch_upstream_config",
    "get_config",
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
