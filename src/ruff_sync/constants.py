"""Constants used across ruff-sync."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Final

from typing_extensions import override

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__: Final[list[str]] = [
    "DEFAULT_BRANCH",
    "DEFAULT_EXCLUDE",
    "DEFAULT_PATH",
    "MISSING",
    "MissingType",
    "OutputFormat",
    "resolve_defaults",
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


@enum.unique
class OutputFormat(str, enum.Enum):
    """Output formats for the CLI."""

    TEXT = "text"
    JSON = "json"
    GITHUB = "github"
    GITLAB = "gitlab"

    @override
    def __str__(self) -> str:
        """Return the string value for argparse help."""
        return self.value


def resolve_defaults(
    branch: str | MissingType,
    path: str | MissingType,
    exclude: Iterable[str] | MissingType,
) -> tuple[str, str | None, Iterable[str]]:
    """Resolve MISSING sentinel values to their effective defaults.

    This is the single source of truth for MISSING → default resolution across
    both ``cli.main`` and ``core._merge_multiple_upstreams``, keeping the two
    layers in sync without introducing a circular dependency between them.

    Args:
        branch: The resolved branch value or ``MISSING``.
        path: The resolved path value or ``MISSING``.
        exclude: The resolved exclude iterable or ``MISSING``.

    Returns:
        A ``(branch, path, exclude)`` tuple with defaults applied.
        ``path`` is normalised to ``None`` (not ``""``) so callers can forward
        it directly to :func:`~ruff_sync.core.resolve_raw_url` and
        :func:`~ruff_sync.core.fetch_upstreams_concurrently`.
    """
    eff_branch = branch if branch is not MISSING else DEFAULT_BRANCH
    raw_path = path if path is not MISSING else DEFAULT_PATH
    # Normalise empty string → None: resolve_raw_url treats both the same,
    # but explicit None is the canonical "root directory" sentinel.
    eff_path: str | None = raw_path or None
    eff_exclude = exclude if exclude is not MISSING else DEFAULT_EXCLUDE
    return eff_branch, eff_path, eff_exclude
