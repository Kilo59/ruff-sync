from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Final, Literal

from invoke.tasks import task
from tomlkit.toml_file import TOMLFile

if TYPE_CHECKING:
    from invoke.context import Context
    from tomlkit import TOMLDocument

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

PROJECT_ROOT: Final[pathlib.Path] = pathlib.Path(__file__).parent
PYPROJECT_TOML: Final[pathlib.Path] = PROJECT_ROOT / "pyproject.toml"
TESTS_DIR: Final[pathlib.Path] = PROJECT_ROOT / "tests"
LIFECYCLE_TOML_DIR: Final[pathlib.Path] = TESTS_DIR / "lifecycle_tomls"


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


@task(aliases=["new-case"])
def new_lifecycle_tomls(ctx: Context, name: str, description: str | None = None) -> None:
    """Create new lifecycle toml test cases using the no_changes tomls as a template"""
    toml_dict: dict[Literal["initial", "upstream", "final"], TOMLDocument] = {
        "initial": TOMLFile(LIFECYCLE_TOML_DIR / "no_changes_initial.toml").read(),
        "upstream": TOMLFile(LIFECYCLE_TOML_DIR / "no_changes_upstream.toml").read(),
        "final": TOMLFile(LIFECYCLE_TOML_DIR / "no_changes_final.toml").read(),
    }
    if not description:
        description = f"Sample project for {name}"
    toml_dict["initial"]["tool"]["poetry"]["name"] = name
    toml_dict["final"]["tool"]["poetry"]["name"] = name
    toml_dict["initial"]["tool"]["poetry"]["description"] = description
    toml_dict["final"]["tool"]["poetry"]["description"] = description

    # write the new tomls
    for stage, toml_doc in toml_dict.items():
        file_name = f"{name}_{stage}.toml"
        if LIFECYCLE_TOML_DIR.joinpath(file_name).exists():
            raise FileExistsError(f"{file_name} already exists")
        TOMLFile(LIFECYCLE_TOML_DIR / file_name).write(toml_doc)
        print(f"📄 {file_name}")
    print(f"🎉 Created tomls for '{name}' test case")
