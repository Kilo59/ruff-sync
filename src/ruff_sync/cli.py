"""Synchronize Ruff linter configuration across Python projects.

This module provides a CLI tool and library for downloading, parsing, and merging
Ruff configuration from upstream sources (like GitHub/GitLab) into local projects.
"""

from __future__ import annotations

import asyncio
import difflib
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections.abc import Iterable, Mapping
from functools import lru_cache
from io import StringIO
from typing import Any, ClassVar, Final, Literal, NamedTuple, TypedDict, cast, overload
from urllib.parse import urlparse

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, table
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile
from typing_extensions import deprecated

__version__ = "0.1.0.dev0"

_DEFAULT_EXCLUDE: Final[set[str]] = {"lint.per-file-ignores"}
_GITHUB_REPO_PATH_PARTS_COUNT: Final[int] = 2
_GITHUB_TREE_PREFIX_PARTS_COUNT: Final[int] = 4
_GITHUB_HOSTS: Final[set[str]] = {"github.com", "www.github.com"}
_GITHUB_RAW_HOST: Final[str] = "raw.githubusercontent.com"
_GITLAB_HOSTS: Final[set[str]] = {"gitlab.com"}

LOGGER = logging.getLogger(__name__)
_HTTP_OK: Final = 200
_HTTP_NOT_FOUND: Final[int] = 404


class ColoredFormatter(logging.Formatter):
    """Logging Formatter to add colors."""

    RESET: ClassVar[str] = "\x1b[0m"
    COLORS: ClassVar[Mapping[int, str]] = {
        logging.DEBUG: "\x1b[36m",  # Cyan
        logging.INFO: "\x1b[32m",  # Green
        logging.WARNING: "\x1b[33m",  # Yellow
        logging.ERROR: "\x1b[31m",  # Red
        logging.CRITICAL: "\x1b[1;31m",  # Bold Red
    }

    def __init__(self, fmt: str = "%(message)s") -> None:
        """Initialize the formatter with a format string."""
        super().__init__(fmt)

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[explicit-override]
        """Format the log record with colors if the output is a TTY."""
        if sys.stderr.isatty():
            color = self.COLORS.get(record.levelno, self.RESET)
            return f"{color}{super().format(record)}{self.RESET}"
        return super().format(record)


class Arguments(NamedTuple):
    """CLI arguments for the ruff-sync tool."""

    command: str
    upstream: URL
    to: pathlib.Path
    exclude: Iterable[str]
    verbose: int
    branch: str = "main"
    path: str = ""
    semantic: bool = False
    diff: bool = True
    init: bool = False

    @property
    @deprecated("Use 'to' instead")
    def source(self) -> pathlib.Path:
        """Deprecated: use 'to' instead."""
        return self.to

    @classmethod
    @lru_cache(maxsize=1)
    def fields(cls) -> set[str]:
        """Return the set of all field names, including deprecated ones."""
        return set(cls._fields) | {"source"}


class FetchResult(NamedTuple):
    """Result of fetching an upstream configuration."""

    buffer: StringIO
    resolved_upstream: URL


class Config(TypedDict, total=False):
    """Configuration schema for [tool.ruff-sync] in pyproject.toml."""

    upstream: str
    to: str
    source: str  # Deprecated
    exclude: list[str]
    verbose: int
    branch: str
    path: str
    semantic: bool
    diff: bool
    init: bool


@lru_cache(maxsize=1)
def get_config(
    source: pathlib.Path,
) -> Config:
    """Read [tool.ruff-sync] configuration from pyproject.toml."""
    local_toml = source / "pyproject.toml"
    # TODO: use pydantic to validate the toml file
    cfg_result: dict[str, Any] = {}
    if local_toml.exists():
        toml = tomlkit.parse(local_toml.read_text())
        config = toml.get("tool", {}).get("ruff-sync")
        if config:
            allowed_keys = set(Config.__annotations__.keys())
            for arg, value in config.items():
                if arg in allowed_keys:
                    if arg == "source":
                        LOGGER.warning(
                            "DeprecationWarning: [tool.ruff-sync] 'source' is deprecated. "
                            "Use 'to' instead."
                        )
                    cfg_result[arg] = value
                else:
                    LOGGER.warning(f"Unknown ruff-sync configuration: {arg}")
            # Ensure 'to' is populated if 'source' was used
            if "source" in cfg_result and "to" not in cfg_result:
                cfg_result["to"] = cfg_result["source"]
    return cast("Config", cfg_result)


def _get_cli_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="ruff-sync",
        description=(
            "Synchronize Ruff linter configuration across Python projects.\n\n"
            "Downloads a pyproject.toml from an upstream URL, extracts the\n"
            "[tool.ruff] section, and merges it into the local pyproject.toml\n"
            "while preserving formatting, comments, and whitespace.\n\n"
            "Defaults to the 'pull' subcommand when none is specified."
        ),
        epilog=(
            "Examples:\n"
            "  ruff-sync pull https://github.com/org/repo/blob/main/pyproject.toml\n"
            "  ruff-sync check https://github.com/org/repo/blob/main/pyproject.toml\n"
            "  ruff-sync pull git@github.com:org/repo.git\n"
            "  ruff-sync pull ssh://git@gitlab.com/org/repo.git\n"
            "  ruff-sync check --semantic  # ignore formatting-only differences\n\n"
            "The upstream URL can also be set in [tool.ruff-sync] in pyproject.toml\n"
            "so you can simply run: ruff-sync pull"
        ),
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run (default: pull)")

    # Common arguments
    common_parser = ArgumentParser(add_help=False)
    common_parser.add_argument(
        "upstream",
        type=URL,
        nargs="?",
        help="The URL to download the pyproject.toml file from."
        " Optional if defined in [tool.ruff-sync].",
    )
    common_parser.add_argument(
        "--to",
        help="The directory or file to sync ruff configuration to. Default: .",
        required=False,
    )
    # Add --source as a deprecated alias
    common_parser.add_argument(
        "--source",
        help="Deprecated alias for --to.",
        required=False,
        metavar="PATH",
    )
    common_parser.add_argument(
        "--exclude",
        nargs="+",
        help=f"Exclude certain ruff configs. Default: {' '.join(_DEFAULT_EXCLUDE)}",
        default=None,
    )
    common_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. -v for INFO, -vv for DEBUG.",
    )
    common_parser.add_argument(
        "--branch",
        help="The default branch to use when resolving repo URLs. Default: main",
        default=None,
    )
    common_parser.add_argument(
        "--path",
        help="The parent path where pyproject.toml is located. Default: root",
        default=None,
    )

    # Pull subcommand (the default action)
    pull_parser = subparsers.add_parser(
        "pull",
        parents=[common_parser],
        help="Pull and apply upstream ruff configuration",
    )
    pull_parser.add_argument(
        "--init",
        action="store_true",
        help="Create a new configuration file if it does not exist in the target directory.",
    )

    # Check subcommand
    check_parser = subparsers.add_parser(
        "check", parents=[common_parser], help="Check if ruff configuration is in sync"
    )
    check_parser.add_argument(
        "--semantic",
        action="store_true",
        help="Ignore non-functional differences like whitespace and comments.",
    )
    check_parser.add_argument(
        "--diff",
        action="store_true",
        default=True,
        help="Show a diff of what would change. Default: True.",
    )
    check_parser.add_argument(
        "--no-diff",
        action="store_false",
        dest="diff",
        help="Do not show a diff.",
    )

    return parser


def _resolve_target_path(to: pathlib.Path, upstream_url: str | URL | None = None) -> pathlib.Path:
    """Resolve the target path for configuration files.

    If 'to' is a file, it's used directly.
    Otherwise, it looks for existing ruff/pyproject.toml in the 'to' directory.
    If none found, it defaults to pyproject.toml unless the upstream is a ruff.toml.
    """
    if to.is_file():
        return to

    # If it's a directory, look for common config files
    for filename in ("ruff.toml", ".ruff.toml", "pyproject.toml"):
        candidate = to / filename
        if candidate.exists():
            return candidate

    # If upstream is specified and is a ruff.toml, default to ruff.toml
    if upstream_url and is_ruff_toml_file(upstream_url):
        return to / "ruff.toml"

    return to / "pyproject.toml"


def _resolve_upstream_target_path(path: str | None) -> str:
    """Resolve the target path for configuration files in upstream repositories.

    If the path indicates a .toml file, it's treated as a direct file path.
    Otherwise, it appends 'pyproject.toml' to the path.
    """
    if not path:
        return "pyproject.toml"

    # Use PurePosixPath to handle URL-style paths consistently
    posix_path = pathlib.PurePosixPath(path.strip("/"))
    if posix_path.suffix == ".toml":
        return str(posix_path)

    return str(posix_path / "pyproject.toml")


def _convert_github_url(url: URL, branch: str = "main", path: str = "") -> URL:
    """Convert a GitHub URL to its corresponding raw content URL.

    Supports:
    - Blob URLs: https://github.com/org/repo/blob/branch/path/to/file
    - Repo URLs: https://github.com/org/repo (defaults to {branch}/{path}/pyproject.toml if path
      doesn't end in .toml)

    Args:
        url (URL): The GitHub URL to be converted.
        branch (str): The default branch to use for repo URLs.
        path (str): The directory prefix for pyproject.toml, or a direct path to a .toml file.

    Returns:
        URL: The corresponding raw content URL.

    """
    # Handle blob URLs (e.g. .../blob/main/pyproject.toml)
    if "/blob/" in url.path:
        new_path = url.path.replace("/blob/", "/", 1)
        raw_url = url.copy_with(host=_GITHUB_RAW_HOST, path=new_path)
        LOGGER.info(f"Converting GitHub blob URL to raw content URL: {raw_url}")
        return raw_url

    # Handle tree URLs (e.g. .../tree/main/path/to/dir)
    if "/tree/" in url.path:
        parts = [p for p in url.path.split("/") if p]
        if len(parts) >= _GITHUB_TREE_PREFIX_PARTS_COUNT and parts[2] == "tree":
            org, repo, _, url_branch = parts[:4]
            url_path = "/".join(parts[4:])
            target_path = _resolve_upstream_target_path(url_path or path)
            raw_url = url.copy_with(
                host=_GITHUB_RAW_HOST,
                path=str(pathlib.PurePosixPath("/", org, repo, url_branch, target_path)),
            )
            LOGGER.info(f"Converting GitHub tree URL to raw content URL: {raw_url}")
            return raw_url

    # Handle repository URLs (e.g. https://github.com/org/repo)
    # We assume if it has exactly two path components, it's a repo URL.
    path_parts = [p for p in url.path.split("/") if p]
    if len(path_parts) == _GITHUB_REPO_PATH_PARTS_COUNT:
        org, repo = path_parts
        target_path = _resolve_upstream_target_path(path)
        raw_url = url.copy_with(
            host=_GITHUB_RAW_HOST,
            path=str(pathlib.PurePosixPath("/", org, repo, branch, target_path)),
        )
        LOGGER.info(f"Converting GitHub repo URL to raw content URL: {raw_url}")
        return raw_url

    LOGGER.info("URL is a GitHub URL but doesn't match known patterns, returning as is.")
    return url


def _convert_gitlab_url(url: URL, branch: str = "main", path: str = "") -> URL:
    """Convert a GitLab URL to its corresponding raw content URL.

    Supports:
    - Blob URLs: https://gitlab.com/org/repo/-/blob/branch/path/to/file
    - Repo URLs: https://gitlab.com/org/repo (defaults to {branch}/{path}/pyproject.toml if path
      doesn't end in .toml)

    Args:
        url (URL): The GitLab URL to be converted.
        branch (str): The default branch to use for repo URLs.
        path (str): The directory prefix for pyproject.toml, or a direct path to a .toml file.

    Returns:
        URL: The corresponding raw content URL.

    """
    # Handle blob URLs (e.g. .../-/blob/main/pyproject.toml)
    if "/-/blob/" in url.path:
        new_path = url.path.replace("/-/blob/", "/-/raw/", 1)
        raw_url = url.copy_with(path=new_path)
        LOGGER.info(f"Converting GitLab blob URL to raw content URL: {raw_url}")
        return raw_url

    # Handle tree URLs (e.g. .../-/tree/main/path/to/dir)
    if "/-/tree/" in url.path:
        parts = [p for p in url.path.split("/") if p]
        try:
            sep_idx = parts.index("-")
            if len(parts) > sep_idx + 2 and parts[sep_idx + 1] == "tree":
                prefix = "/" + "/".join(parts[:sep_idx])
                url_branch = parts[sep_idx + 2]
                url_path = "/".join(parts[sep_idx + 3 :])
                target_path = _resolve_upstream_target_path(url_path or path)
                raw_url = url.copy_with(
                    path=str(pathlib.PurePosixPath(prefix, "-", "raw", url_branch, target_path))
                )
                LOGGER.info(f"Converting GitLab tree URL to raw content URL: {raw_url}")
                return raw_url
        except ValueError:
            pass

    # Handle repository URLs (e.g. https://gitlab.com/org/repo)
    # If the path doesn't contain the separator '/-/', we assume it's a project root.
    if "/-/" not in url.path:
        # Avoid empty paths or just a slash
        path_prefix = url.path.rstrip("/")
        if path_prefix:
            target_path = _resolve_upstream_target_path(path)
            raw_url = url.copy_with(
                path=str(pathlib.PurePosixPath(path_prefix, "-", "raw", branch, target_path))
            )
            LOGGER.info(f"Converting GitLab repo URL to raw content URL: {raw_url}")
            return raw_url

    LOGGER.info("URL is a GitLab URL but doesn't match known patterns, returning as is.")
    return url


def is_git_url(url: URL) -> bool:
    """Return True if the URL should be treated as a git repository."""
    return str(url).startswith("git@") or url.scheme in ("ssh", "git", "git+ssh")


def to_git_url(url: URL) -> URL | None:
    """Attempt to convert a browser or raw URL to a git (SSH) URL.

    Supports GitHub and GitLab.
    """
    if is_git_url(url):
        return url

    if url.host in _GITHUB_HOSTS or url.host == _GITHUB_RAW_HOST:
        path_parts = [p for p in url.path.split("/") if p]
        if len(path_parts) >= _GITHUB_REPO_PATH_PARTS_COUNT:
            org, repo = path_parts[:_GITHUB_REPO_PATH_PARTS_COUNT]
            repo = repo.removesuffix(".git")
            return URL(f"git@github.com:{org}/{repo}.git")

    if url.host in _GITLAB_HOSTS:
        path = url.path.strip("/")
        project_path = path.split("/-/")[0] if "/-/" in path else path
        if project_path:
            project_path = project_path.removesuffix(".git")
            return URL(f"git@{url.host}:{project_path}.git")

    return None


def resolve_raw_url(url: URL, branch: str = "main", path: str | None = None) -> URL:
    """Convert a GitHub or GitLab repository/blob URL to a raw content URL.

    Args:
        url (URL): The URL to resolve.
        branch (str): The default branch to use for repo URLs.
        path (str | None): The directory prefix for pyproject.toml.

    Returns:
        URL: The resolved raw content URL, or the original URL if no conversion applies.

    """
    # If it's a git URL, leave it alone; we'll handle it via git clone
    if is_git_url(url):
        return url
    LOGGER.debug(f"Initial URL: {url}")
    if url.host in _GITHUB_HOSTS:
        return _convert_github_url(url, branch=branch, path=path or "")
    if url.host in _GITLAB_HOSTS:
        return _convert_gitlab_url(url, branch=branch, path=path or "")
    return url


async def download(url: URL, client: httpx.AsyncClient) -> StringIO:
    """Download a file from a URL and return a StringIO object."""
    response = await client.get(url)
    response.raise_for_status()
    return StringIO(response.text)


async def _download_with_discovery(url: URL, client: httpx.AsyncClient, branch: str) -> FetchResult:
    """Download config from a URL, trying common filenames if a directory guess fails."""
    # For HTTP URLs, try candidates if it looks like a directory guess
    candidates = [url]

    # If the URL was a guess (resolved from a directory or repo root), try other names
    if pathlib.PurePosixPath(url.path).name == "pyproject.toml":
        # Try pyproject.toml first to satisfy most projects and existing tests,
        # then fall back to ruff.toml variants.
        base_url = url.join(".")
        candidates = [
            url,  # pyproject.toml is first
            base_url.join("ruff.toml"),
            base_url.join(".ruff.toml"),
        ]

    for candidate_url in candidates:
        response = await client.get(candidate_url)
        if response.status_code == _HTTP_OK:
            return FetchResult(StringIO(response.text), candidate_url)

        if response.status_code != _HTTP_NOT_FOUND or candidate_url == candidates[-1]:
            # If it's not a 404, or the last candidate failed, raise
            response.raise_for_status()

    # Should not reach here if candidates is not empty
    msg = "Configuration discovery failed without error"
    raise RuntimeError(msg)


def _fetch_via_git(url: URL, branch: str, path: str | None) -> FetchResult:
    """Clone the git repo into a temp directory and read config.

    Uses an efficient cloning strategy to minimize network traffic and disk space.

    Returns:
        FetchResult: (content buffer, resolved path string)

    """
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use --no-checkout and --filter=blob:none to avoid downloading unnecessary files
        cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--no-checkout",
            "--branch",
            branch,
            str(url),
            temp_dir,
        ]
        LOGGER.info(f"Running git command: {' '.join(cmd)}")
        try:
            subprocess.run(  # noqa: S603
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            target_path = pathlib.Path(_resolve_upstream_target_path(path))

            # For git clone, we also want to try candidates if target_path is guessed
            candidates = [target_path]
            if target_path.name == "pyproject.toml":
                configs_dir = target_path.parent
                candidates = [
                    target_path,  # pyproject.toml is first
                    configs_dir / "ruff.toml",
                    configs_dir / ".ruff.toml",
                ]

            for cand_path in candidates:
                # Restore just the config file
                full_path = pathlib.Path(temp_dir) / cand_path
                restore_cmd = [
                    "git",
                    "-C",
                    temp_dir,
                    "restore",
                    "--source",
                    branch,
                    str(cand_path),
                ]
                try:
                    subprocess.run(  # noqa: S603
                        restore_cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    if full_path.exists():
                        return FetchResult(StringIO(full_path.read_text()), URL(str(cand_path)))
                except subprocess.CalledProcessError:
                    # Fallback for old git
                    checkout_cmd = [
                        "git",
                        "-C",
                        temp_dir,
                        "checkout",
                        branch,
                        "--",
                        str(cand_path),
                    ]
                    try:
                        subprocess.run(  # noqa: S603
                            checkout_cmd,
                            check=True,
                            capture_output=True,
                            text=True,
                        )
                        if full_path.exists():
                            return FetchResult(StringIO(full_path.read_text()), URL(str(cand_path)))
                    except subprocess.CalledProcessError:
                        continue

            msg = f"Configuration file not found in repository at {target_path}"
            raise FileNotFoundError(msg)
        except subprocess.CalledProcessError as e:
            LOGGER.exception(f"Git operation failed: {e.stderr}")
            raise


async def fetch_upstream_config(
    url: URL, client: httpx.AsyncClient, branch: str, path: str | None
) -> FetchResult:
    """Fetch the upstream pyproject.toml either via HTTP or git clone."""
    if is_git_url(url):
        LOGGER.info(f"Cloning {url} via git...")
        return await asyncio.to_thread(_fetch_via_git, url, branch, path)

    try:
        return await _download_with_discovery(url, client, branch)
    except httpx.HTTPStatusError as err:
        msg = f"HTTP error {err.response.status_code} when downloading from {url}"
        git_url = to_git_url(url)
        if git_url:
            # sys.argv[1] might be -v or something else when running via pytest
            try:
                cmd = sys.argv[1]
                if cmd not in ("pull", "check"):
                    cmd = "pull"
            except IndexError:
                cmd = "pull"
            msg += (
                f"\n\n💡 Check the URL and your permissions. "
                "You might want to try cloning via git instead:\n\n"
                f"   ruff-sync {cmd} {git_url}"
            )
        else:
            msg += "\n\n💡 Check the URL and your permissions."

        # Re-raise with a more helpful message while preserving the original exception context
        raise httpx.HTTPStatusError(msg, request=err.request, response=err.response) from None


def is_ruff_toml_file(path_or_url: str | URL) -> bool:
    """Return True if the path or URL indicates a ruff.toml file.

    This handles:
    - Plain paths (e.g. "ruff.toml", ".ruff.toml", "configs/ruff.toml")
    - URLs with query strings or fragments (e.g. "ruff.toml?ref=main", "ruff.toml#L10")
    by examining only the path component (or the part before any query/fragment).
    """
    parsed = urlparse(str(path_or_url))

    # If it's a URL with a scheme/netloc, use the parsed path component.
    # Otherwise, fall back to stripping any query/fragment from the raw string.
    if parsed.scheme or parsed.netloc:
        path = parsed.path
    else:
        path = str(path_or_url).split("?", 1)[0].split("#", 1)[0]

    return pathlib.Path(path).name in ("ruff.toml", ".ruff.toml")


@overload
def get_ruff_config(
    toml: str | TOMLDocument,
    is_ruff_toml: bool = ...,
    create_if_missing: Literal[True] = ...,
    exclude: Iterable[str] = ...,
) -> TOMLDocument | Table: ...


@overload
def get_ruff_config(
    toml: str | TOMLDocument,
    is_ruff_toml: bool = ...,
    create_if_missing: Literal[False] = ...,
    exclude: Iterable[str] = ...,
) -> TOMLDocument | Table | None: ...


def get_ruff_config(
    toml: str | TOMLDocument,
    is_ruff_toml: bool = False,
    create_if_missing: bool = True,
    exclude: Iterable[str] = (),
) -> TOMLDocument | Table | None:
    """Get the ruff section or document from a TOML string.

    If it does not exist and it is a pyproject.toml, create it.
    """
    if isinstance(toml, str):
        doc: TOMLDocument = tomlkit.parse(toml)
    else:
        doc = toml

    if is_ruff_toml:
        _apply_exclusions(doc, exclude)
        return doc

    try:
        tool: Table = doc["tool"]  # type: ignore[assignment]
        ruff = tool["ruff"]
        LOGGER.debug("Found `tool.ruff` section.")
    except KeyError:
        if not create_if_missing:
            return None
        LOGGER.info("✨ No `tool.ruff` section found, creating it.")
        tool = table(True)
        ruff = table()
        tool.append("ruff", ruff)
        doc.append("tool", tool)
    if not isinstance(ruff, Table):
        msg = f"Expected table, got {type(ruff)}"
        raise TypeError(msg)
    _apply_exclusions(ruff, exclude)
    return ruff


# Alias for backward compatibility in internal tools/tests if they exist
get_ruff_tool_table = get_ruff_config


def _apply_exclusions(tbl: Table | TOMLDocument, exclude: Iterable[str]) -> None:
    """Remove excluded keys from a ruff table, supporting dotted paths.

    Keys can be simple (e.g. ``"target-version"``) to match top-level ruff
    keys, or dotted (e.g. ``"lint.per-file-ignores"``) to reach into nested
    sub-tables.
    """
    for key_path in exclude:
        parts = key_path.split(".")
        target: Any = tbl
        for part in parts[:-1]:
            target = target.get(part) if hasattr(target, "get") else None
            if target is None:
                break
        if target is not None and hasattr(target, "pop"):
            leaf = parts[-1]
            if leaf in target:
                LOGGER.info(f"Excluding `{key_path}` from upstream ruff config.")
                target.pop(leaf)


def toml_ruff_parse(toml_s: str, exclude: Iterable[str]) -> TOMLDocument:
    """Parse a TOML string for the tool.ruff section excluding certain ruff configs."""
    ruff_toml: TOMLDocument = tomlkit.parse(toml_s)["tool"]["ruff"]  # type: ignore[index,assignment]
    for section in exclude:
        LOGGER.info(f"Excluding section `lint.{section}` from ruff config.")
        ruff_toml["lint"].pop(section, None)  # type: ignore[union-attr]
    return ruff_toml


def _recursive_update(source_table: Any, upstream: Any) -> None:
    """Recursively update a TOML table, preserving formatting of existing keys."""
    if hasattr(upstream, "items") or isinstance(upstream, Mapping):
        items = upstream.items()
    else:
        return

    for key, value in items:
        if key in source_table:
            if hasattr(source_table[key], "items") and (
                hasattr(value, "items") or isinstance(value, Mapping)
            ):
                # Structural fix: if the target is a proxy (dotted key),
                # and we are adding NEW keys to it, we must convert it to a real
                # table to ensure children get correct headers.
                source_sub_keys = set(source_table[key].keys())
                upstream_sub_keys = set(value.keys())
                if not upstream_sub_keys.issubset(source_sub_keys):
                    current_val = source_table[key].unwrap()
                    # DELETE PROXY FIRST to avoid structural doubling
                    del source_table[key]
                    # ADD AS REAL TABLE
                    source_table.add(key, current_val)

                _recursive_update(source_table[key], value)
            else:
                # Overwrite existing leaf value only if it's semantically different.
                # Compare unwrapped values, but assign the raw tomlkit Item to
                # preserve inline comments attached to the upstream value.
                current_val = (
                    source_table[key].unwrap()
                    if hasattr(source_table[key], "unwrap")
                    else source_table[key]
                )
                new_val_unwrapped = value.unwrap() if hasattr(value, "unwrap") else value
                if current_val != new_val_unwrapped:
                    source_table[key] = value
        else:
            # New key: assign the raw tomlkit Item to preserve comments
            source_table[key] = value


def merge_ruff_toml(
    source: TOMLDocument,
    upstream_ruff_doc: TOMLDocument | Table | None,
    is_ruff_toml: bool = False,
) -> TOMLDocument:
    """Merge the source and upstream tool ruff config with better whitespace preservation."""
    if not upstream_ruff_doc:
        LOGGER.warning("No upstream ruff config section found.")
        return source

    if is_ruff_toml:
        _recursive_update(source, upstream_ruff_doc)
        return source

    source_tool_ruff = get_ruff_config(source, create_if_missing=True)

    _recursive_update(source_tool_ruff, upstream_ruff_doc)

    # Add a blank separator line after the ruff section — but only when another
    # top-level section follows it. Adding \n\n at end-of-file is unnecessary.
    doc_str = source.as_string()
    ruff_start = doc_str.find("[tool.ruff]")
    # Look for any non-ruff top-level section header after [tool.ruff]
    ruff_is_last = ruff_start == -1 or not re.search(
        r"^\[(?!tool\.ruff)", doc_str[ruff_start:], re.MULTILINE
    )
    if not ruff_is_last and not source_tool_ruff.as_string().endswith("\n\n"):
        source_tool_ruff.add(tomlkit.nl())

    return source


async def check(
    args: Arguments,
) -> int:
    """Check if the local pyproject.toml / ruff.toml is in sync with the upstream."""
    print("🔍 Checking Ruff sync status...")

    _source_toml_path = _resolve_target_path(args.to, args.upstream).resolve(strict=False)
    if not _source_toml_path.exists():
        print(
            f"❌ Configuration file {_source_toml_path} does not exist. "
            "Run 'ruff-sync pull' to create it."
        )
        return 1

    source_toml_file = TOMLFile(_source_toml_path)
    source_doc = source_toml_file.read()

    async with httpx.AsyncClient() as client:
        fetch_result = await fetch_upstream_config(
            args.upstream, client, branch=args.branch, path=args.path
        )
        LOGGER.info(f"Loaded upstream file from {fetch_result.resolved_upstream}")

    is_upstream_ruff_toml = is_ruff_toml_file(fetch_result.resolved_upstream)
    is_source_ruff_toml = is_ruff_toml_file(_source_toml_path.name)

    upstream_ruff_toml = get_ruff_config(
        fetch_result.buffer.read(),
        is_ruff_toml=is_upstream_ruff_toml,
        create_if_missing=False,
        exclude=args.exclude,
    )

    # Create a copy for comparison
    source_doc_copy = tomlkit.parse(source_doc.as_string())
    merged_doc = merge_ruff_toml(
        source_doc_copy,
        upstream_ruff_toml,
        is_ruff_toml=is_source_ruff_toml,
    )

    if args.semantic:
        if is_source_ruff_toml:
            source_ruff = source_doc
            merged_ruff = merged_doc
        else:
            source_ruff = source_doc.get("tool", {}).get("ruff")
            merged_ruff = merged_doc.get("tool", {}).get("ruff")

        # Compare unwrapped versions
        source_val = source_ruff.unwrap() if source_ruff is not None else None
        merged_val = merged_ruff.unwrap() if merged_ruff is not None else None

        if source_val == merged_val:
            print("✅ Ruff configuration is semantically in sync.")
            return 0
    elif source_doc.as_string() == merged_doc.as_string():
        print("✅ Ruff configuration is in sync.")
        return 0

    try:
        rel_path = _source_toml_path.relative_to(pathlib.Path.cwd())
    except ValueError:
        rel_path = _source_toml_path
    print(f"❌ Ruff configuration at {rel_path} is out of sync!")
    if args.diff:
        if args.semantic:
            # Semantic diff of the managed section
            from_lines = json.dumps(source_val, indent=2, sort_keys=True).splitlines(keepends=True)
            to_lines = json.dumps(merged_val, indent=2, sort_keys=True).splitlines(keepends=True)
            from_file = "local (semantic)"
            to_file = "upstream (semantic)"
        else:
            # Full text diff of the file
            from_lines = source_doc.as_string().splitlines(keepends=True)
            to_lines = merged_doc.as_string().splitlines(keepends=True)
            from_file = f"local/{_source_toml_path.name}"
            to_file = f"upstream/{_source_toml_path.name}"

        diff = difflib.unified_diff(
            from_lines,
            to_lines,
            fromfile=from_file,
            tofile=to_file,
        )
        sys.stdout.writelines(diff)
    return 1


async def pull(
    args: Arguments,
) -> int:
    """Pull the upstream ruff config and apply it to the source."""
    print("🔄 Syncing Ruff...")
    _source_toml_path = _resolve_target_path(args.to, args.upstream).resolve(strict=False)

    source_toml_file = TOMLFile(_source_toml_path)
    if _source_toml_path.exists():
        source_doc = source_toml_file.read()
    elif args.init:
        LOGGER.info(f"✨ Target file {_source_toml_path} does not exist, creating it.")
        source_doc = tomlkit.document()
        # Scaffold the file immediately to ensure we can write to the enclosing directory
        try:
            _source_toml_path.parent.mkdir(parents=True, exist_ok=True)
            _source_toml_path.touch()
        except OSError as e:
            print(f"❌ Failed to create {_source_toml_path}: {e}", file=sys.stderr)
            return 1
    else:
        print(
            f"❌ Configuration file {_source_toml_path} does not exist. "
            "Pass the '--init' flag to create it."
        )
        return 1

    # NOTE: there's no particular reason to use async here.
    async with httpx.AsyncClient() as client:
        fetch_result = await fetch_upstream_config(
            args.upstream, client, branch=args.branch, path=args.path
        )
        LOGGER.info(f"Loaded upstream file from {fetch_result.resolved_upstream}")

    is_upstream_ruff_toml = is_ruff_toml_file(fetch_result.resolved_upstream)
    is_source_ruff_toml = is_ruff_toml_file(_source_toml_path.name)

    upstream_ruff_toml = get_ruff_config(
        fetch_result.buffer.read(),
        is_ruff_toml=is_upstream_ruff_toml,
        create_if_missing=False,
        exclude=args.exclude,
    )
    merged_toml = merge_ruff_toml(
        source_doc,
        upstream_ruff_toml,
        is_ruff_toml=is_source_ruff_toml,
    )
    source_toml_file.write(merged_toml)
    try:
        rel_path = _source_toml_path.resolve().relative_to(pathlib.Path.cwd())
    except ValueError:
        rel_path = _source_toml_path.resolve()
    print(f"✅ Updated {rel_path}")
    return 0


PARSER: Final[ArgumentParser] = _get_cli_parser()


def _resolve_upstream(args: Any, config: Mapping[str, Any]) -> URL:
    """Resolve upstream URL from CLI or config."""
    if args.upstream:
        return cast("URL", args.upstream)
    if "upstream" in config:
        config_upstream = config["upstream"]
        if not isinstance(config_upstream, str):
            PARSER.error(
                "❌ upstream in [tool.ruff-sync] must be a string, "
                f"got {type(config_upstream).__name__}"
            )
        upstream = URL(config_upstream)
        LOGGER.info(f"📂 Using upstream from [tool.ruff-sync]: {upstream}")
        return upstream
    PARSER.error(
        "❌ the following arguments are required: upstream "
        "(or define it in [tool.ruff-sync] in pyproject.toml) 💥"
    )


def _resolve_exclude(args: Any, config: Mapping[str, Any]) -> Iterable[str]:
    """Resolve exclude patterns from CLI, config, or default."""
    if args.exclude is not None:
        return cast("Iterable[str]", args.exclude)
    if "exclude" in config:
        exclude = config["exclude"]
        LOGGER.info(f"🚫 Using exclude from [tool.ruff-sync]: {list(exclude)}")
        return cast("Iterable[str]", exclude)
    return _DEFAULT_EXCLUDE


def _resolve_branch(args: Any, config: Mapping[str, Any]) -> str:
    """Resolve branch name from CLI, config, or default."""
    if args.branch:
        return cast("str", args.branch)
    if "branch" in config:
        branch = cast("str", config["branch"])
        LOGGER.info(f"🌿 Using branch from [tool.ruff-sync]: {branch}")
        return branch
    return "main"


def _resolve_path(args: Any, config: Mapping[str, Any]) -> str:
    """Resolve path prefix from CLI, config, or default."""
    if args.path:
        return cast("str", args.path)
    if "path" in config:
        path = cast("str", config["path"])
        LOGGER.info(f"📄 Using path from [tool.ruff-sync]: {path}")
        return path
    return ""


def _resolve_to(args: Any, config: Mapping[str, Any], initial_to: pathlib.Path) -> pathlib.Path:
    """Resolve target path from CLI, config, or default."""
    if args.source:
        LOGGER.warning("DeprecationWarning: --source is deprecated. Use --to instead.")
        return pathlib.Path(args.source)
    if args.to:
        return pathlib.Path(args.to)
    if "to" in config:
        target = pathlib.Path(config["to"])
        # Resolve relative to the directory where we found the config file
        base_dir = initial_to.parent if initial_to.is_file() else initial_to
        resolved = base_dir / target
        LOGGER.info(f"🎯 Using target path from [tool.ruff-sync]: {resolved}")
        return resolved
    return initial_to


def _resolve_args(
    args: Any, config: Mapping[str, Any], initial_to: pathlib.Path
) -> tuple[URL, pathlib.Path, Iterable[str], str, str]:
    """Resolve upstream, to, exclude, branch, and path from CLI and config."""
    upstream = _resolve_upstream(args, config)
    to = _resolve_to(args, config, initial_to)
    exclude = _resolve_exclude(args, config)
    branch = _resolve_branch(args, config)
    path = _resolve_path(args, config)
    return upstream, to, exclude, branch, path


def main() -> int:
    """Run the ruff-sync CLI."""
    # Handle backward compatibility: default to 'pull' if no command provided
    if len(sys.argv) > 1 and sys.argv[1] not in (
        "pull",
        "check",
        "-h",
        "--help",
        "--version",
    ):
        sys.argv.insert(1, "pull")
    elif len(sys.argv) == 1:
        sys.argv.append("pull")

    args = PARSER.parse_args()

    # Configure logging
    log_level = {
        0: logging.WARNING,
        1: logging.INFO,
    }.get(args.verbose, logging.DEBUG)

    LOGGER.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter())
    LOGGER.addHandler(handler)
    LOGGER.propagate = "PYTEST_CURRENT_TEST" in os.environ  # Allow capturing in tests

    # Determine target 'to' from CLI or use default '.'
    # Defer Path conversion to avoid pyfakefs issues with captured Path class
    arg_to = args.to or args.source
    initial_to = pathlib.Path(arg_to) if arg_to else pathlib.Path()
    config: Config = get_config(initial_to)

    upstream, to_val, exclude, branch, path = _resolve_args(args, config, initial_to)

    # Convert non-raw github/gitlab upstream url to the raw equivalent
    upstream = resolve_raw_url(upstream, branch=branch, path=path)

    # Create Arguments object
    exec_args = Arguments(
        command=args.command,
        upstream=upstream,
        to=to_val,
        exclude=exclude,
        verbose=args.verbose,
        branch=branch,
        path=path,
        semantic=getattr(args, "semantic", False),
        diff=getattr(args, "diff", True),
        init=getattr(args, "init", False),
    )

    if exec_args.command == "check":
        return asyncio.run(check(exec_args))
    return asyncio.run(pull(exec_args))


if __name__ == "__main__":
    sys.exit(main())
