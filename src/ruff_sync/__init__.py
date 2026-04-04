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
from .config_io import (
    RuffConfigFileName,
    is_ruff_toml_file,
    load_local_ruff_config,
    resolve_target_path,
)
from .constants import OutputFormat
from .core import (
    Config,
    FetchResult,
    check,
    fetch_upstream_config,
    get_ruff_config,
    get_ruff_tool_table,
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
    "load_local_ruff_config",
    "main",
    "merge_ruff_toml",
    "pull",
    "resolve_raw_url",
    "resolve_target_path",
    "to_git_url",
    "toml_ruff_parse",
]
