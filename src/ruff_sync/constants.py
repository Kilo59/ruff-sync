"""Constants used across ruff-sync."""

from __future__ import annotations

import enum
from typing import Final

__all__: Final[list[str]] = [
    "DEFAULT_BRANCH",
    "DEFAULT_EXCLUDE",
    "DEFAULT_PATH",
    "MISSING",
    "MissingType",
]

DEFAULT_EXCLUDE: Final[set[str]] = {"lint.per-file-ignores"}
DEFAULT_BRANCH: Final[str] = "main"
DEFAULT_PATH: Final[str] = ""


class MissingType(enum.Enum):
    """Used to represent a missing value sentinel.

    This can be used to properly type fields that use the `MissingType.SENTINEL` as a default.

    Example:
        >>> from ruff_sync.constants import MissingType, MISSING
        >>> def foo(bar: int | None | MissingType = MISSING) -> None:
        ...     if bar is MissingType.SENTINEL:
        ...         print("bar is missing")
        ...     else:
        ...         print(f"bar is {bar}")
    """

    SENTINEL = enum.auto()


MISSING: Final[MissingType] = MissingType.SENTINEL
