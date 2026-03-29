"""Core logic for ruff-sync."""

from __future__ import annotations

import asyncio
import difflib
import enum
import json
import logging
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping
from io import StringIO
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Literal,
    NamedTuple,
    TypedDict,
    overload,
)
from urllib.parse import urlparse

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, table
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile
from typing_extensions import override

from ruff_sync.constants import (
    DEFAULT_BRANCH,
    MISSING,
    resolve_defaults,
)
from ruff_sync.formatters import ResultFormatter, get_formatter
from ruff_sync.pre_commit import sync_pre_commit

if TYPE_CHECKING:
    from ruff_sync.cli import Arguments

__all__: Final[list[str]] = [
    "Config",
    "FetchResult",
    "RuffConfigFileName",
    "UpstreamError",
    "check",
    "fetch_upstream_config",
    "fetch_upstreams_concurrently",
    "get_ruff_config",
    "get_ruff_tool_table",
    "is_ruff_toml_file",
    "merge_ruff_toml",
    "pull",
    "resolve_raw_url",
    "resolve_target_path",
    "serialize_ruff_sync_config",
    "to_git_url",
    "toml_ruff_parse",
]

LOGGER = logging.getLogger(__name__)

_GITHUB_REPO_PATH_PARTS_COUNT: Final[int] = 2
_GITHUB_TREE_PREFIX_PARTS_COUNT: Final[int] = 4
_GITHUB_HOSTS: Final[set[str]] = {"github.com", "www.github.com"}
_GITHUB_RAW_HOST: Final[str] = "raw.githubusercontent.com"
_GITLAB_HOSTS: Final[set[str]] = {"gitlab.com"}

_HTTP_OK: Final = 200
_HTTP_NOT_FOUND: Final[int] = 404


@enum.unique
class RuffConfigFileName(str, enum.Enum):
    """Enumeration of Ruff configuration filenames."""

    PYPROJECT_TOML = "pyproject.toml"
    RUFF_TOML = "ruff.toml"
    DOT_RUFF_TOML = ".ruff.toml"

    @classmethod
    def tried_order(cls) -> list[RuffConfigFileName]:
        """Return the order in which configuration files should be tried."""
        return [cls.RUFF_TOML, cls.DOT_RUFF_TOML, cls.PYPROJECT_TOML]

    @override
    def __str__(self) -> str:
        """Return the filename as a string."""
        return self.value


class FetchResult(NamedTuple):
    """Result of fetching an upstream configuration."""

    buffer: StringIO
    resolved_upstream: URL


class UpstreamError(Exception):
    """Raised when one or more upstream fetches fail.

    Attributes:
        errors: A tuple of tuples containing the URL and the BaseException that occurred.
    """

    def __init__(self, errors: Iterable[tuple[URL, BaseException]]) -> None:
        """Initialize UpstreamError with a list of fetch failures."""
        self.errors: Final[tuple[tuple[URL, BaseException], ...]] = tuple(errors)
        error_count = len(self.errors)
        msg = f"❌ {error_count} upstream fetch{'es' if error_count > 1 else ''} failed"
        super().__init__(msg)


class Config(TypedDict, total=False):
    """Configuration schema for [tool.ruff-sync] in pyproject.toml."""

    upstream: str | list[str]
    to: str
    source: str  # Deprecated
    exclude: list[str]
    verbose: int
    branch: str
    path: str
    semantic: bool
    diff: bool
    init: bool
    pre_commit_version_sync: bool


def resolve_target_path(
    to: pathlib.Path, upstreams: Iterable[str | URL] | None = None
) -> pathlib.Path:
    """Resolve the target path for configuration files.

    If 'to' is a file, it's used directly.
    Otherwise, it looks for existing ruff/pyproject.toml in the 'to' directory.
    If none found, it defaults to pyproject.toml unless the first upstream is a ruff.toml.
    """
    if to.is_file():
        return to

    # If it's a directory, look for common config files
    for filename in RuffConfigFileName.tried_order():
        candidate = to / filename
        if candidate.exists():
            return candidate

    # Use the first upstream URL as a hint for the default file name
    first_upstream = next(iter(upstreams), None) if upstreams else None

    # If upstream is specified and is a ruff.toml, default to ruff.toml
    if first_upstream and is_ruff_toml_file(first_upstream):
        return to / RuffConfigFileName.RUFF_TOML

    return to / RuffConfigFileName.PYPROJECT_TOML


def _resolve_upstream_target_path(path: str | None) -> str:
    """Resolve the target path for configuration files in upstream repositories.

    If the path indicates a .toml file, it's treated as a direct file path.
    Otherwise, it appends 'pyproject.toml' to the path.
    """
    if not path:
        return RuffConfigFileName.PYPROJECT_TOML

    # Use PurePosixPath to handle URL-style paths consistently
    posix_path = pathlib.PurePosixPath(path.strip("/"))
    if posix_path.suffix == ".toml":
        return str(posix_path)

    return str(posix_path / RuffConfigFileName.PYPROJECT_TOML)


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


@overload
def _get_discovery_candidates(base: URL) -> list[URL]: ...


@overload
def _get_discovery_candidates(base: pathlib.Path) -> list[pathlib.Path]: ...


def _get_discovery_candidates(base: URL | pathlib.Path) -> list[URL] | list[pathlib.Path]:
    """Return a list of candidate configuration files, prioritizing the requested one."""
    # If it's a URL, use PurePosixPath. If it's a Path, use it directly.
    name = base.path if isinstance(base, URL) else base.name
    if pathlib.PurePosixPath(name).name != RuffConfigFileName.PYPROJECT_TOML:
        return [base]  # type: ignore[return-value]

    # Try pyproject.toml first, then fall back to ruff.toml variants.
    if isinstance(base, URL):
        base_url = base.join(".")
        return [base] + [
            base_url.join(str(f))
            for f in RuffConfigFileName.tried_order()
            if str(f) != RuffConfigFileName.PYPROJECT_TOML
        ]

    configs_dir = base.parent
    return [base] + [
        configs_dir / str(f)
        for f in RuffConfigFileName.tried_order()
        if str(f) != RuffConfigFileName.PYPROJECT_TOML
    ]


async def _download_with_discovery(url: URL, client: httpx.AsyncClient, branch: str) -> FetchResult:
    """Download config from a URL, trying common filenames if a directory guess fails."""
    candidates = _get_discovery_candidates(url)

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
            candidates = _get_discovery_candidates(target_path)

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

    return pathlib.Path(path).name in (
        RuffConfigFileName.RUFF_TOML,
        RuffConfigFileName.DOT_RUFF_TOML,
    )


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
    r"""Merge the source and upstream tool ruff config with better whitespace preservation.

    Examples:
        >>> from tomlkit import parse
        >>> source = parse("[tool.ruff]\nline-length = 80")
        >>> upstream = parse("[tool.ruff]\nline-length = 100")["tool"]["ruff"]
        >>> merged = merge_ruff_toml(source, upstream)
        >>> print(merged.as_string())
        [tool.ruff]
        line-length = 100
    """
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


async def fetch_upstreams_concurrently(
    upstreams: Iterable[URL],
    client: httpx.AsyncClient,
    branch: str = DEFAULT_BRANCH,
    path: str | None = None,
) -> list[FetchResult]:
    """Fetch multiple upstream configurations concurrently.

    Uses asyncio.TaskGroup if available (Python 3.11+), otherwise falls
    back to asyncio.gather.

    Args:
        upstreams: The URLs to fetch.
        client: The HTTPX async client to use.
        branch: The default branch for repo-root URLs.
        path: The directory prefix for pyproject.toml in repo-root URLs.

    Returns:
        A list of FetchResult objects in the same order as the input upstreams.

    Raises:
        UpstreamError: If one or more upstreams fail to fetch.
    """
    upstream_list = list(upstreams)
    if sys.version_info >= (3, 11):
        # Use structured concurrency on Python 3.11+
        tasks: list[asyncio.Task[FetchResult]] = []
        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    tg.create_task(fetch_upstream_config(url, client, branch, path))
                    for url in upstream_list
                ]
            return [t.result() for t in tasks]
        except BaseException as eg:
            if isinstance(eg, (asyncio.CancelledError, KeyboardInterrupt)):
                raise
            # TODO: Use `except*` once Python 3.11+ is the minimum supported version.
            # On Python 3.11+, TaskGroup raises an ExceptionGroup.
            # Catching it as Exception is safe and compatible with Python 3.10 syntax.
            errors = [
                (upstream_list[i], t.exception())
                for i, t in enumerate(tasks)
                if t.done() and t.exception() is not None
            ]
            if errors:
                raise UpstreamError(errors) from eg
            raise
    else:
        # Fallback for Python 3.10
        fetch_tasks = [fetch_upstream_config(url, client, branch, path) for url in upstream_list]
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        errors_list: list[tuple[URL, BaseException]] = []
        fetch_results: list[FetchResult] = []

        for i, res in enumerate(results):
            if isinstance(res, BaseException):
                errors_list.append((upstream_list[i], res))
            elif isinstance(res, FetchResult):
                fetch_results.append(res)
            else:
                msg = f"Unexpected result type from fetch: {type(res)}"
                raise TypeError(msg)

        if errors_list:
            raise UpstreamError(errors_list)

        return fetch_results


def _resolve_defaults(
    args: Arguments,
) -> tuple[str, str | None, Iterable[str]]:
    """Resolve MISSING sentinel values in *args* to their effective defaults.

    Delegates to :func:`~ruff_sync.constants.resolve_defaults` so that the
    MISSING → default logic is centralised in one place and shared with
    ``cli.main`` without coupling the two layers together.
    """
    return resolve_defaults(args.branch, args.path, args.exclude)


async def _merge_multiple_upstreams(
    target_doc: TOMLDocument,
    is_target_ruff_toml: bool,
    args: Arguments,
    client: httpx.AsyncClient,
) -> TOMLDocument:
    """Fetch and merge all upstreams into the target document.

    Downloads are performed concurrently via fetch_upstreams_concurrently,
    while merging remains sequential to preserve layering order.
    """
    branch, path, exclude = _resolve_defaults(args)

    fetch_results = await fetch_upstreams_concurrently(
        args.upstream, client, branch=branch, path=path
    )

    # Sequentially merge the results in the original order
    for fetch_result in fetch_results:
        LOGGER.info(f"Loaded upstream file from {fetch_result.resolved_upstream}")

        is_upstream_ruff_toml = is_ruff_toml_file(fetch_result.resolved_upstream)

        upstream_ruff_toml = get_ruff_config(
            fetch_result.buffer.read(),
            is_ruff_toml=is_upstream_ruff_toml,
            create_if_missing=False,
            exclude=exclude,
        )

        target_doc = merge_ruff_toml(
            target_doc, upstream_ruff_toml, is_ruff_toml=is_target_ruff_toml
        )
    return target_doc


def _print_diff(
    args: Arguments,
    source_toml_path: pathlib.Path,
    source_doc: tomlkit.TOMLDocument,
    merged_doc: tomlkit.TOMLDocument,
    source_val: Any,
    merged_val: Any,
) -> None:
    """Print the unified diff between the local and expected configurations."""
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
        from_file = f"local/{source_toml_path.name}"
        to_file = f"upstream/{source_toml_path.name}"

    diff = difflib.unified_diff(
        from_lines,
        to_lines,
        fromfile=from_file,
        tofile=to_file,
    )
    sys.stdout.writelines(diff)


def _check_pre_commit_sync(args: Arguments, fmt: ResultFormatter) -> int | None:
    """Return exit code 2 if pre-commit hook version is out of sync, otherwise None.

    Shared helper to avoid duplicating the pre-commit synchronization logic.
    """
    if getattr(args, "pre_commit", False) and not sync_pre_commit(pathlib.Path.cwd(), dry_run=True):
        fmt.warning("⚠️ Pre-commit hook version is out of sync!")
        return 2
    return None


async def check(
    args: Arguments,
) -> int:
    """Check if the local pyproject.toml / ruff.toml is in sync with the upstream.

    Returns:
        int: 0 if in sync, 1 if out of sync.

    Examples:
        >>> import asyncio
        >>> from ruff_sync.cli import Arguments
        >>> from httpx import URL
        >>> import pathlib
        >>> args = Arguments(
        ...     command="check",
        ...     upstream=URL("https://github.com/org/repo/blob/main/pyproject.toml"),
        ...     to=pathlib.Path("pyproject.toml"),
        ...     exclude=[],
        ... )
        >>> # asyncio.run(check(args))
    """
    fmt = get_formatter(args.output_format)
    fmt.info("🔍 Checking Ruff sync status...")

    _source_toml_path = resolve_target_path(args.to, args.upstream).resolve(strict=False)
    if not _source_toml_path.exists():
        fmt.error(
            f"❌ Configuration file {_source_toml_path} does not exist. "
            "Run 'ruff-sync pull' to create it.",
            file_path=_source_toml_path,
        )
        return 1

    source_toml_file = TOMLFile(_source_toml_path)
    source_doc = source_toml_file.read()

    # Create a copy for comparison
    source_doc_copy = tomlkit.parse(source_doc.as_string())
    merged_doc = source_doc_copy

    async with httpx.AsyncClient() as client:
        merged_doc = await _merge_multiple_upstreams(
            merged_doc,
            is_target_ruff_toml=is_ruff_toml_file(_source_toml_path.name),
            args=args,
            client=client,
        )

    is_source_ruff_toml = is_ruff_toml_file(_source_toml_path.name)
    source_val: Any = None
    merged_val: Any = None
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
            fmt.success("✅ Ruff configuration is semantically in sync.")
            exit_code = _check_pre_commit_sync(args, fmt)
            if exit_code is not None:
                return exit_code
            return 0
    elif source_doc.as_string() == merged_doc.as_string():
        fmt.success("✅ Ruff configuration is in sync.")
        exit_code = _check_pre_commit_sync(args, fmt)
        if exit_code is not None:
            return exit_code
        return 0

    try:
        rel_path = _source_toml_path.relative_to(pathlib.Path.cwd())
    except ValueError:
        rel_path = _source_toml_path
    fmt.error(f"❌ Ruff configuration at {rel_path} is out of sync!", file_path=rel_path)

    if args.diff:
        _print_diff(
            args=args,
            source_toml_path=_source_toml_path,
            source_doc=source_doc,
            merged_doc=merged_doc,
            source_val=source_val,
            merged_val=merged_val,
        )
    return 1


def _get_credential_url(upstreams: tuple[URL, ...]) -> URL | None:
    for url in upstreams:
        if url.username or url.password:
            return url
    return None


def _get_or_create_ruff_sync_table(doc: TOMLDocument) -> tomlkit.items.Table:
    tool_table = doc.get("tool")
    if not isinstance(tool_table, tomlkit.items.Table):
        tool_table = tomlkit.table()
        # Use assignment (not append) so we replace rather than duplicate the key
        doc["tool"] = tool_table

    ruff_sync_table = tool_table.get("ruff-sync")
    if not isinstance(ruff_sync_table, tomlkit.items.Table):
        ruff_sync_table = tomlkit.table()
        # Use assignment (not add) so we replace rather than raise KeyAlreadyPresent
        tool_table["ruff-sync"] = ruff_sync_table

    return ruff_sync_table


def serialize_ruff_sync_config(doc: TOMLDocument, args: Arguments) -> None:
    """Serialize the ruff-sync CLI arguments into the TOML document."""
    bad_url = _get_credential_url(args.upstream)
    if bad_url:
        suggested = to_git_url(bad_url)
        suggestion_msg = f" (e.g., {suggested})" if suggested else ""
        LOGGER.warning(
            "⚠️ Upstream URL contains credentials! Refusing to serialize "
            f"[tool.ruff-sync] configuration. Consider using a SSH git URL instead{suggestion_msg}"
            " to avoid leaking credentials."
        )
        return

    ruff_sync_table = _get_or_create_ruff_sync_table(doc)

    # TODO: Consider only saving upstream if it differs from existing config
    if len(args.upstream) == 1:
        ruff_sync_table["upstream"] = str(args.upstream[0])
    else:
        urls_array = tomlkit.array()
        urls_array.multiline(True)
        for url in args.upstream:
            urls_array.append(str(url))
        ruff_sync_table["upstream"] = urls_array

    # Normalize excludes and de-duplicate while preserving order.
    # Only compute and persist excludes when explicitly provided so that
    # DEFAULT_EXCLUDE remains an implicit default and is not serialized.
    if args.exclude is not MISSING:
        normalized_excludes = list(dict.fromkeys(args.exclude))
        exclude_array = tomlkit.array()
        for ex in normalized_excludes:
            exclude_array.append(ex)
        ruff_sync_table["exclude"] = exclude_array

    if args.branch is not MISSING:
        ruff_sync_table["branch"] = args.branch

    if args.path is not MISSING:
        ruff_sync_table["path"] = args.path

    if args.pre_commit is not MISSING:
        ruff_sync_table["pre-commit-version-sync"] = args.pre_commit


async def pull(
    args: Arguments,
) -> int:
    """Pull the upstream ruff config and apply it to the source.

    Returns:
        int: 0 on success, 1 on failure.

    Examples:
        >>> import asyncio
        >>> from ruff_sync.cli import Arguments
        >>> from httpx import URL
        >>> import pathlib
        >>> args = Arguments(
        ...     command="pull",
        ...     upstream=URL("https://github.com/org/repo/blob/main/pyproject.toml"),
        ...     to=pathlib.Path("pyproject.toml"),
        ...     exclude=["lint.isort"],
        ...     init=True,
        ... )
        >>> # asyncio.run(pull(args))
    """
    print("🔄 Syncing Ruff...")
    _source_toml_path = resolve_target_path(args.to, args.upstream).resolve(strict=False)

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

    async with httpx.AsyncClient() as client:
        source_doc = await _merge_multiple_upstreams(
            source_doc,
            is_target_ruff_toml=is_ruff_toml_file(_source_toml_path.name),
            args=args,
            client=client,
        )

    should_save = args.save if args.save is not None else args.init
    if should_save:
        if _source_toml_path.name == RuffConfigFileName.PYPROJECT_TOML:
            LOGGER.info(f"Saving [tool.ruff-sync] configuration to {_source_toml_path.name}")
            serialize_ruff_sync_config(source_doc, args)
        else:
            LOGGER.info(
                "Skipping [tool.ruff-sync] configuration save because target is not pyproject.toml"
            )

    source_toml_file.write(source_doc)
    try:
        rel_path = _source_toml_path.resolve().relative_to(pathlib.Path.cwd())
    except ValueError:
        rel_path = _source_toml_path.resolve()
    print(f"✅ Updated {rel_path}")

    if args.pre_commit is not MISSING and args.pre_commit:
        sync_pre_commit(pathlib.Path.cwd(), dry_run=False)

    return 0
