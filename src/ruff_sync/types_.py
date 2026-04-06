"""Core data types and TypedDicts for ruff-sync."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from typing_extensions import NotRequired

RuleSyncStatus = Literal["Enabled", "Ignored", "Disabled"]


class RuffRule(TypedDict):
    """Represents a single Ruff rule as returned by `ruff rule --all --output-format json`."""

    code: str
    name: str
    linter: str
    summary: str
    explanation: NotRequired[str]
    fix_availability: NotRequired[str]
    status: NotRequired[RuleSyncStatus | dict[str, Any]]
    matching_select: NotRequired[str | None]
    matching_ignore: NotRequired[str | None]
    preview: NotRequired[bool]


class RuffLinter(TypedDict):
    """Represents a Ruff linter category as returned by `ruff linter --output-format json`."""

    prefix: NotRequired[str]
    name: str
    url: NotRequired[str]
    categories: NotRequired[list[RuffLinter]]
