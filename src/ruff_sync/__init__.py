"""Ruff sync package.

This package provides tools to synchronize ruff configuration across projects.
"""

from __future__ import annotations

from .cli import (
    _DEFAULT_EXCLUDE,
    LOGGER,
    Arguments,
    ColoredFormatter,
    Config,
    FetchResult,
    __version__,
    _resolve_target_path,
    check,
    download,
    fetch_upstream_config,
    get_config,
    get_ruff_config,
    get_ruff_tool_table,
    is_git_url,
    is_ruff_toml_file,
    main,
    merge_ruff_toml,
    pull,
    resolve_raw_url,
    to_git_url,
    toml_ruff_parse,
)

__all__ = [
    "LOGGER",
    "_DEFAULT_EXCLUDE",
    "Arguments",
    "ColoredFormatter",
    "Config",
    "FetchResult",
    "__version__",
    "_resolve_target_path",
    "check",
    "download",
    "fetch_upstream_config",
    "get_config",
    "get_ruff_config",
    "get_ruff_tool_table",
    "is_git_url",
    "is_ruff_toml_file",
    "main",
    "merge_ruff_toml",
    "pull",
    "resolve_raw_url",
    "to_git_url",
    "toml_ruff_parse",
]
