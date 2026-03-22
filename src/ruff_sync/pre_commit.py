"""Pre-commit hook synchronization logic."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Final

import tomlkit

if TYPE_CHECKING:
    import pathlib

__all__: Final[list[str]] = [
    "resolve_ruff_version",
    "sync_pre_commit",
]

LOGGER = logging.getLogger(__name__)


def _get_locked_version(lockfile: pathlib.Path) -> str | None:
    """Extract Ruff version from a uv.lock file."""
    if not lockfile.exists():
        return None
    try:
        data = tomlkit.parse(lockfile.read_text(encoding="utf-8"))
        # uv.lock puts packages in a [[package]] list
        packages = data.get("package", [])
        for pkg in packages:
            if pkg.get("name") == "ruff":
                return str(pkg.get("version"))
    except Exception as e:
        LOGGER.debug(f"Failed to parse lockfile {lockfile}: {e}")
    return None


def _get_pyproject_version(pyproject: pathlib.Path) -> str | None:
    """Extract Ruff version constraint from pyproject.toml."""
    if not pyproject.exists():
        return None
    try:
        data = tomlkit.parse(pyproject.read_text(encoding="utf-8"))
        deps = list(data.get("project", {}).get("dependencies", []))

        opt_deps = data.get("project", {}).get("optional-dependencies", {})
        for opt_group in opt_deps.values():
            if isinstance(opt_group, list):
                deps.extend(opt_group)

        groups = data.get("dependency-groups", {})
        for group_deps in groups.values():
            if isinstance(group_deps, list):
                deps.extend(group_deps)

        # Simple extraction: look for ruff>=X.Y.Z, ruff == X.Y.Z, ruff~=X.Y.Z, etc.
        for dep in deps:
            if isinstance(dep, str) and dep.startswith("ruff"):
                match = re.search(r"ruff\s*[>=~^]+\s*([0-9A-Za-z._-]+)", dep)
                if match:
                    return match.group(1)
    except Exception as e:
        LOGGER.debug(f"Failed to parse dependencies in {pyproject}: {e}")
    return None


def resolve_ruff_version(base_dir: pathlib.Path) -> str | None:
    """Resolve the Ruff version for the project from lockfile or pyproject.toml."""
    # Strategy 1: exact pinned version from uv.lock
    lock_version = _get_locked_version(base_dir / "uv.lock")
    if lock_version:
        LOGGER.info(f"🔒 Found Ruff version {lock_version} in uv.lock")
        return lock_version

    # Strategy 2: version constraint from pyproject.toml
    pyproject_version = _get_pyproject_version(base_dir / "pyproject.toml")
    if pyproject_version:
        LOGGER.info(f"📄 Found Ruff version {pyproject_version} constraint in pyproject.toml")
        return pyproject_version

    return None


def sync_pre_commit(base_dir: pathlib.Path, dry_run: bool = False) -> bool:
    """Sync the local .pre-commit-config.yaml with the project's Ruff version.

    Returns:
        bool: True if in sync, False if out of sync (and optionally updated).
    """
    config_file = base_dir / ".pre-commit-config.yaml"
    if not config_file.exists():
        LOGGER.debug("No .pre-commit-config.yaml found, skipping sync.")
        return True

    version = resolve_ruff_version(base_dir)
    if not version:
        LOGGER.warning("Could not resolve project Ruff version for pre-commit sync.")
        return True  # cannot do anything

    content = config_file.read_text(encoding="utf-8")

    # Match the ruff-pre-commit repo and its rev key within the same YAML block,
    # allowing for additional keys, comments, and varying layout between them.
    # This looks for a "repo: https://github.com/astral-sh/ruff-pre-commit" line,
    # followed by any number of indented lines, and then a "rev:" key at the same
    # indentation level as the other entries in that repo block.
    pattern = re.compile(
        r"(repo:\s*https://github\.com/astral-sh/ruff-pre-commit[^\n]*\n"
        r"(?:[ \t].*\n)*?"
        r"[ \t]*rev:\s*)(['\"]?[a-zA-Z0-9_.-]+['\"]?)",
        re.MULTILINE,
    )
    match = pattern.search(content)

    if not match:
        LOGGER.debug("ruff-pre-commit not found in .pre-commit-config.yaml")
        return True

    current_rev = match.group(2).strip("'\"")
    target_rev = f"v{version}" if not version.startswith("v") else version

    # If the current_rev doesn't start with v, then strip v from target_rev (keep style)
    if not current_rev.startswith("v") and target_rev.startswith("v"):
        target_rev = target_rev[1:]

    if current_rev == target_rev:
        LOGGER.info(f"✨ pre-commit Ruff hook is already in sync ({current_rev})")
        return True

    if dry_run:
        LOGGER.warning(
            f"❌ pre-commit Ruff hook is out of sync "
            f"(current: {current_rev}, expected: {target_rev})"
        )
        return False

    # Needs quotes if the original had them
    if '"' in match.group(2):
        new_rev_str = f'"{target_rev}"'
    elif "'" in match.group(2):
        new_rev_str = f"'{target_rev}'"
    else:
        new_rev_str = target_rev

    LOGGER.info(f"🔄 Updating pre-commit Ruff hook from {current_rev} to {target_rev}")
    new_content = content[: match.start(2)] + new_rev_str + content[match.end(2) :]
    config_file.write_text(new_content, encoding="utf-8")

    return True
