"""Development tasks for ruff-sync.

This module provides Invoke tasks for linting, formatting, type checking, and
managing releases of the ruff-sync package.

https://www.pyinvoke.org/
https://docs.pyinvoke.org/en/stable/
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import TYPE_CHECKING, Final, Literal

import httpx
from invoke.exceptions import Exit
from invoke.tasks import task
from packaging.version import Version
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
    """Format code with ruff format."""
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
    """Lint and fix code with ruff."""
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
    """Type check code with mypy."""
    cmds = ["mypy"]
    if install_types:
        cmds.append("--install-types")
    if check:
        cmds.extend(["--pretty"])
    ctx.run(" ".join(cmds), echo=True, pty=True)


@task(aliases=["sync"])
def deps(ctx: Context) -> None:
    """Sync dependencies with uv lock file."""
    ctx.run("uv sync", echo=True, pty=True)


def _get_current_version() -> str:
    """Read the current version from pyproject.toml."""
    with PYPROJECT_TOML.open("r", encoding="utf-8") as f:
        toml_content = TOMLFile(f.name).read()
    return str(toml_content["project"]["version"])  # type: ignore[index]


def _get_pypi_versions() -> tuple[str | None, str | None]:
    """Fetch current and previous versions from PyPI."""
    try:
        r = httpx.get("https://pypi.org/pypi/ruff-sync/json", timeout=5.0)
        data = r.json()
        current = str(data["info"]["version"])
        # PEP 440-aware sorting of version strings
        all_v = sorted(data["releases"].keys(), key=Version)
        pv = None
        if current in all_v:
            idx = all_v.index(current)
            if idx > 0:
                pv = all_v[idx - 1]
        elif all_v:
            pv = all_v[-1]
    except Exception:
        return None, None
    else:
        return current, pv


def _get_latest_gh_release(ctx: Context) -> str | None:
    """Get the latest GitHub release tag name."""
    try:
        # Use gh cli to get the latest tag name
        cmd = "gh release list --limit 1 --json tagName --jq '.[0].tagName'"
        result = ctx.run(cmd, hide=True)
        if result:
            return result.stdout.strip()
    except Exception:
        return None
    return None


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
    current_branch = branch_result.stdout.strip()
    if not dry_run and current_branch != "main":
        print(f"❌ Releases must be made from the 'main' branch (current: {current_branch}).")
        return

    # Check for dirty git state
    status_result = ctx.run("git status --porcelain", hide=True)
    git_status = status_result.stdout.strip()
    if git_status:
        print("❌ Git repository has uncommitted changes. Please commit or stash them first.")
        return

    if not skip_tests:
        print("🚀 Running validation suite...")
        lint(ctx, check=True)
        fmt(ctx, check=True)
        type_check(ctx, check=True)
        ctx.run("uv run pytest", echo=True, pty=True)

    version = _get_current_version()
    print(f"Current local version: {version}")

    # Show remote versions
    latest_gh = _get_latest_gh_release(ctx)
    pypi_curr, pypi_prev = _get_pypi_versions()

    print(f"Latest GitHub release:  {latest_gh or 'None'}")
    print(f"Current PyPI version:   {pypi_curr or 'None'}")
    print(f"Previous PyPI version:  {pypi_prev or 'None'}")
    print("-" * 40)

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
    """Create new lifecycle toml test cases using the no_changes tomls as a template."""
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
            msg = f"{file_name} already exists"
            raise FileExistsError(msg)
        TOMLFile(LIFECYCLE_TOML_DIR / file_name).write(toml_doc)
        print(f"📄 {file_name}")
    print(f"🎉 Created tomls for '{name}' test case")


@task(
    help={
        "serve": "Build and serve the documentation locally (default if no flags)",
        "build": "Build the documentation to the site/ directory",
        "args": "Additional flags to pass to mkdocs (e.g. '--strict --dirtyreload')",
    }
)
def docs(ctx: Context, *, serve: bool = False, build: bool = False, args: str = "") -> None:
    """Build or serve the documentation."""
    # Reject invalid combination of mutually exclusive flags
    if serve and build:
        msg = "Options --serve and --build are mutually exclusive; please specify only one."
        raise Exit(msg)

    # Default to serve if no flags provided
    if not (serve or build):
        serve = True

    cmds = ["mkdocs"]
    if build:
        cmds.append("build")
    elif serve:
        cmds.append("serve")

    if args:
        cmds.extend(args.split())

    ctx.run("uv run " + " ".join(cmds), echo=True, pty=True)


@task
def screenshots(ctx: Context) -> None:
    """Automatically generate TUI screenshots for documentation."""
    # Ensure the screenshots directory exists
    ctx.run("mkdir -p docs/assets/screenshots/", echo=True)
    # Run the official generation script
    ctx.run("uv run python scripts/generate_tui_screenshots.py", echo=True, pty=True)
    print("✨ Documentation screenshots updated in docs/assets/screenshots/")


@task(
    help={
        "tape": "Specific tape file to record (e.g. 'pull_basic'). Default: all tapes.",
    },
)
def recordings(ctx: Context, tape: str | None = None) -> None:
    """Regenerate CLI animation GIFs from VHS tape files."""
    import pathlib

    tapes_dir = pathlib.Path("tapes")
    if not tapes_dir.exists():
        print("❌ tapes/ directory not found. Run from the project root.")
        raise Exit(code=1)

    # Check VHS is installed
    vhs_cmd = "vhs"
    result = ctx.run("which vhs", hide=True, warn=True, pty=False, in_stream=False)
    if not result.ok:
        # Try common Homebrew paths
        for p in ["/opt/homebrew/bin/vhs", "/usr/local/bin/vhs"]:
            if pathlib.Path(p).exists():
                vhs_cmd = p
                break
        else:
            print("❌ VHS is not installed. Install with: brew install vhs")
            raise Exit(code=1)

    if tape:
        tape_file = tapes_dir / f"{tape}.tape"
        if not tape_file.exists():
            print(f"❌ Tape file not found: {tape_file}")
            raise Exit(code=1)
        tape_files = [tape_file]
    else:
        # Process all tape files except _common.tape
        tape_files = sorted(f for f in tapes_dir.glob("*.tape") if not f.name.startswith("_"))

    if not tape_files:
        print("⚠️ No tape files found in tapes/")
        return

    print(f"🎬 Recording {len(tape_files)} tape(s)...")
    env = os.environ.copy()
    homebrew_bin = "/opt/homebrew/bin:/usr/local/bin"
    env["PATH"] = f"{homebrew_bin}:{env.get('PATH', '')}"

    for tf in tape_files:
        print(f"  📼 {tf.name}")
        ctx.run(f"{vhs_cmd} {tf}", in_stream=False, env=env)

    print("\n🎉 All recordings complete!")
    print("   Output: docs/assets/recordings/")
