from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Final

from invoke.tasks import task

if TYPE_CHECKING:
    from invoke.context import Context

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

PROJECT_ROOT: Final[pathlib.Path] = pathlib.Path(__file__).parent
PYPROJECT_TOML: Final[pathlib.Path] = PROJECT_ROOT / "pyproject.toml"


@task
def fmt(ctx: Context, check: bool = False) -> None:
    """Format code with ruff format"""
    cmds = ["ruff", "format", "."]
    if check:
        cmds.append("--check")
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(
    help={
        "check": "Check code without fixing it",
        "unsafe-fixes": "Apply 'un-safe' fixes. See https://docs.astral.sh/ruff/linter/#fix-safety",
    }
)
def lint(ctx: Context, check: bool = False, unsafe_fixes: bool = False) -> None:
    """Lint and fix code with ruff"""
    cmds = ["ruff", "."]
    if not check:
        cmds.append("--fix")
    if unsafe_fixes:
        cmds.extend(["--unsafe-fixes", "--show-fixes"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(
    aliases=["types"],
)
def type_check(ctx: Context, install_types: bool = False, check: bool = False) -> None:
    """Type check code with mypy"""
    cmds = ["mypy"]
    if install_types:
        cmds.append("--install-types")
    if check:
        cmds.extend(["--pretty"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(aliases=["sync"])
def deps(ctx: Context) -> None:
    """Sync dependencies with poetry lock file"""
    # using --with dev incase poetry changes the default behavior
    cmds = ["poetry", "install", "--sync", "--with", "dev"]
    ctx.run(" ".join(cmds), echo=True, pty=True)
