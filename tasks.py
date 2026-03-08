from __future__ import annotations

import logging
import pathlib
from typing import TYPE_CHECKING, Any, Final, Literal, cast

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
def fmt(ctx: Context, *, check: bool = False) -> None:
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
def lint(ctx: Context, *, check: bool = False, unsafe_fixes: bool = False) -> None:
    """Lint and fix code with ruff"""
    cmds = ["ruff", "check", "."]
    if not check:
        cmds.append("--fix")
    if unsafe_fixes:
        cmds.extend(["--unsafe-fixes", "--show-fixes"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(
    aliases=["types"],
)
def type_check(ctx: Context, *, install_types: bool = False, check: bool = False) -> None:
    """Type check code with mypy"""
    cmds = ["mypy"]
    if install_types:
        cmds.append("--install-types")
    if check:
        cmds.extend(["--pretty"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(aliases=["sync"])
def deps(ctx: Context) -> None:
    """Sync dependencies with uv lock file"""
    ctx.run("uv sync", echo=True, pty=True)


def _get_current_version() -> str:
    """Read the current version from pyproject.toml"""
    with PYPROJECT_TOML.open("r", encoding="utf-8") as f:
        toml_content = TOMLFile(f.name).read()
    return str(toml_content["project"]["version"])  # type: ignore[index]


@task(
    help={
        "dry-run": "Show what would be done without making changes.",
        "skip-tests": "Skip running tests and linting before release.",
        "draft": "Create the release as a draft on GitHub (default: True).",
    }
)
def release(
    ctx: Context,
    dry_run: bool = True,
    skip_tests: bool = False,
    draft: bool = True,
) -> None:
    """Tag and create a GitHub release for the current project version."""
    # Check if we are on the main branch
    branch_result = ctx.run("git branch --show-current", hide=True)
    current_branch = cast("Any", branch_result).stdout.strip()
    if not dry_run and current_branch != "main":
        print(
            f"❌ Releases must be made from the 'main' branch "
            f"(current: {current_branch})."
        )
        return

    # Check for dirty git state
    status_result = ctx.run("git status --porcelain", hide=True)
    git_status = cast("Any", status_result).stdout.strip()
    if git_status:
        print(
            "❌ Git repository has uncommitted changes. "
            "Please commit or stash them first."
        )
        return

    if not skip_tests:
        print("🚀 Running validation suite...")
        lint(ctx, check=True)
        fmt(ctx, check=True)
        type_check(ctx, check=True)
        ctx.run("uv run pytest", echo=True, pty=True)

    version = _get_current_version()
    print(f"Releasing version: {version}")

    if dry_run:
        print(f"⚠️  DRY RUN: Would create a release for v{version}")
        return

    # Create GitHub release
    print(f"📦 Creating GitHub release for v{version}...")
    gh_cmd = f"gh release create v{version} --generate-notes"
    if draft:
        gh_cmd += " --draft"

    ctx.run(gh_cmd, echo=True)

    print(f"🎉 Version {version} released successfully!")


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
    toml_dict["initial"]["tool"]["poetry"]["name"] = name  # type: ignore[index]
    toml_dict["final"]["tool"]["poetry"]["name"] = name  # type: ignore[index]
    toml_dict["initial"]["tool"]["poetry"]["description"] = description  # type: ignore[index]
    toml_dict["final"]["tool"]["poetry"]["description"] = description  # type: ignore[index]

    # write the new tomls
    for stage, toml_doc in toml_dict.items():
        file_name = f"{name}_{stage}.toml"
        if LIFECYCLE_TOML_DIR.joinpath(file_name).exists():
            raise FileExistsError(f"{file_name} already exists")
        TOMLFile(LIFECYCLE_TOML_DIR / file_name).write(toml_doc)
        print(f"📄 {file_name}")
    print(f"🎉 Created tomls for '{name}' test case")
