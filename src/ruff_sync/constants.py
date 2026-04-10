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
    "ConfKey",
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
    SARIF = "sarif"

    @override
    def __str__(self) -> str:
        """Return the string value for argparse help."""
        return self.value


@enum.unique
class ConfKey(str, enum.Enum):
    """Centralized configuration keys for [tool.ruff-sync].

    These are the canonical names used in the pyproject.toml configuration file.
    """

    UPSTREAM = "upstream"
    TO = "to"
    EXCLUDE = "exclude"
    BRANCH = "branch"
    PATH = "path"
    PRE_COMMIT_VERSION_SYNC = "pre-commit-version-sync"
    OUTPUT_FORMAT = "output-format"
    SEMANTIC = "semantic"
    DIFF = "diff"
    INIT = "init"
    SAVE = "save"
    VERBOSE = "verbose"
    VALIDATE = "validate"
    STRICT = "strict"

    # Legacy / Alias Keys
    SOURCE = "source"  # Legacy for 'to'
    PRE_COMMIT = "pre-commit"  # Legacy for 'pre-commit-version-sync'
    PRE_COMMIT_SYNC_LEGACY = "pre-commit-sync"  # Legacy for 'pre-commit-version-sync'

    @override
    def __str__(self) -> str:
        """Return the string value for TOML keys."""
        return self.value

    @classmethod
    def to_attr(cls, key: str | ConfKey) -> str:
        """Normalize a configuration key to its Python attribute name (underscore)."""
        return str(key).replace("-", "_")

    @classmethod
    def get_canonical(cls, key: str) -> str:
        """Map legacy or aliased configuration keys to their canonical names.

        Args:
            key: The raw key from the configuration file.

        Returns:
            The canonical ConfKey name (still as a string for use in logic).
        """
        # Normalize the input key to underscores for robust alias matching
        norm_key = cls.to_attr(key)

        # Handle aliases for 'to'
        if norm_key == cls.to_attr(cls.SOURCE):
            return cls.TO.value

        # Handle aliases for 'pre-commit-version-sync'
        if norm_key in (
            cls.to_attr(cls.PRE_COMMIT_SYNC_LEGACY),
            cls.to_attr(cls.PRE_COMMIT),
        ):
            return cls.PRE_COMMIT_VERSION_SYNC.value

        # Return the original key (even if unknown, let 'allowed_keys' handle it)
        return key


def resolve_defaults(
    branch: str | MissingType,
    path: str | None | MissingType,
    exclude: Iterable[str] | MissingType,
) -> tuple[str, str | None, Iterable[str]]:
    """Resolve MISSING sentinel values to their effective defaults.

    This is the single source of truth for MISSING → default resolution for
    URL-related parameters (branch, path, exclude).

    Args:
        branch: The resolved branch value or ``MISSING``.
        path: The resolved path value or ``MISSING``.
        exclude: The resolved exclude iterable or ``MISSING``.

    Returns:
        A ``(branch, path, exclude)`` tuple with defaults applied.
        ``path`` is normalised to ``None`` (not ``""``) so callers can forward
        it directly to :func:`~ruff_sync.core.resolve_raw_url`.
    """
    eff_branch = branch if branch is not MISSING else DEFAULT_BRANCH
    raw_path = path if path is not MISSING else DEFAULT_PATH
    # Normalise empty string → None: resolve_raw_url treats both the same,
    # but explicit None is the canonical "root directory" sentinel.
    eff_path: str | None = raw_path or None
    eff_exclude = exclude if exclude is not MISSING else DEFAULT_EXCLUDE

    return eff_branch, eff_path, eff_exclude


def apply_bool_precedence(
    validate: bool | MissingType, strict: bool | MissingType
) -> tuple[bool | MissingType, bool | MissingType]:
    """Apply precedence rules for validate and strict flags.

    1. Disabling validation implicitly disables strict mode.
    2. Strict mode implicitly enables validation.
    """
    if validate is False:
        strict = False
    elif strict is True:
        validate = True
    return validate, strict


def resolve_bool_flags(
    validate: bool | MissingType = MISSING,
    strict: bool | MissingType = MISSING,
    pre_commit: bool | MissingType = MISSING,
) -> tuple[bool, bool, bool]:
    """Resolve MISSING sentinel values for boolean execution flags.

    Returns:
        A ``(validate, strict, pre_commit)`` tuple with defaults applied.
        ``strict=True`` implicitly enables ``validate``.
    """
    validate, strict = apply_bool_precedence(validate, strict)

    eff_validate = validate if validate is not MISSING else False
    eff_strict = strict if strict is not MISSING else False
    eff_pre_commit = pre_commit if pre_commit is not MISSING else False

    return eff_validate, eff_strict, eff_pre_commit
