"""Configuration file discovery and loading logic."""

from __future__ import annotations

import enum
import pathlib
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import tomlkit
from tomlkit.items import Table
from typing_extensions import override

if TYPE_CHECKING:
    from httpx import URL


@enum.unique
class RuffConfigFileName(str, enum.Enum):
    """Enumeration of Ruff configuration filenames."""

    PYPROJECT_TOML = "pyproject.toml"
    RUFF_TOML = "ruff.toml"
    DOT_RUFF_TOML = ".ruff.toml"

    @classmethod
    def tried_order(cls) -> list[RuffConfigFileName]:
        """Return the order in which configuration files should be tried."""
        return [cls.RUFF_TOML, cls.DOT_RUFF_TOML, cls.PYPROJECT_TOML]

    @override
    def __str__(self) -> str:
        """Return the filename as a string."""
        return self.value


def is_ruff_toml_file(path_or_url: str | URL) -> bool:
    """Return True if the path or URL indicates a ruff.toml file.

    This handles cases with query strings or fragments by examining only the path component.
    """
    parsed = urlparse(str(path_or_url))

    # If it's a URL with a scheme/netloc, use the parsed path component.
    # Otherwise, fall back to stripping any query/fragment from the raw string.
    if parsed.scheme or parsed.netloc:
        path = parsed.path
    else:
        path = str(path_or_url).split("?", 1)[0].split("#", 1)[0]

    return pathlib.Path(path).name in (
        RuffConfigFileName.RUFF_TOML,
        RuffConfigFileName.DOT_RUFF_TOML,
    )


def resolve_target_path(
    to: pathlib.Path, upstreams: Iterable[str | URL] | None = None
) -> pathlib.Path:
    """Resolve the target path for configuration files.

    If 'to' is a file, it's used directly.
    Otherwise, it looks for existing ruff/pyproject.toml in the 'to' directory.
    If none found, it defaults to pyproject.toml unless the first upstream is a ruff.toml.
    """
    if to.is_file():
        return to

    # If it's a directory, look for common config files
    for filename in RuffConfigFileName.tried_order():
        candidate = to / filename
        if candidate.exists():
            return candidate

    # Use the first upstream URL as a hint for the default file name
    first_upstream = next(iter(upstreams), None) if upstreams else None

    # If upstream is specified and is a ruff.toml, default to ruff.toml
    if first_upstream and is_ruff_toml_file(first_upstream):
        return to / RuffConfigFileName.RUFF_TOML

    return to / RuffConfigFileName.PYPROJECT_TOML


def load_local_ruff_config(target: pathlib.Path) -> dict[str, Any]:
    """Load the local Ruff configuration as a plain dictionary.

    Args:
        target: The directory or file path to load configuration from.

    Returns:
        A plain dictionary containing the [tool.ruff] configuration.

    Raises:
        FileNotFoundError: If no configuration file is found at the target path.
        TypeError: If the configuration structure is invalid.
    """
    config_path = resolve_target_path(target)
    if not config_path.exists():
        msg = f"No Ruff configuration file found at: {config_path}"
        raise FileNotFoundError(msg)

    content = config_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    is_ruff_toml = config_path.name in (
        RuffConfigFileName.RUFF_TOML,
        RuffConfigFileName.DOT_RUFF_TOML,
    )

    if is_ruff_toml:
        # For ruff.toml, the entire document is the configuration
        unwrapped = doc.unwrap() if hasattr(doc, "unwrap") else doc
        return unwrapped if isinstance(unwrapped, dict) else {}

    # For pyproject.toml, extract [tool.ruff]
    try:
        # We use isinstance checks instead of cast to satisfy mypy
        tool = doc.get("tool")
        if not isinstance(tool, Mapping):
            return {}
        ruff = tool.get("ruff")
        if ruff is None:
            return {}
        if not isinstance(ruff, (Mapping, Table)):
            msg = f"Expected table for [tool.ruff], got {type(ruff)}"
            raise TypeError(msg)

        data = ruff.unwrap() if hasattr(ruff, "unwrap") else ruff
        if not isinstance(data, dict):
            return {}
    except KeyError:
        return {}
    else:
        return data
