"""Synchronize Ruff linter configuration across Python projects.

This module provides a CLI tool and library for downloading, parsing, and merging
Ruff configuration from upstream sources (like GitHub/GitLab) into local projects.
"""

from __future__ import annotations

import asyncio
import logging
import os
import pathlib
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    NamedTuple,
    cast,
)

import tomlkit
from httpx import URL
from typing_extensions import deprecated

from ruff_sync.core import (
    Config,
    RuffConfigFileName,
    check,
    pull,
    resolve_raw_url,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__all__: Final[list[str]] = [
    "Arguments",
    "ColoredFormatter",
    "get_config",
    "main",
]

__version__ = "0.1.0.dev2"

LOGGER = logging.getLogger(__name__)

_DEFAULT_EXCLUDE: Final[set[str]] = {"lint.per-file-ignores"}


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
    upstream: tuple[URL, ...]
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


@lru_cache(maxsize=1)
def get_config(
    source: pathlib.Path,
) -> Config:
    """Read [tool.ruff-sync] configuration from pyproject.toml.

    Examples:
        >>> import pathlib
        >>> config = get_config(pathlib.Path("."))
        >>> if "upstream" in config:
        ...     print(f"Syncing from {config['upstream']}")
    """
    local_toml = source / RuffConfigFileName.PYPROJECT_TOML
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
            f"Downloads a {RuffConfigFileName.PYPROJECT_TOML} from an upstream URL, "
            "extracts the\n"
            "[tool.ruff] section, and merges it into the local "
            f"{RuffConfigFileName.PYPROJECT_TOML}\n"
            "while preserving formatting, comments, and whitespace.\n\n"
            "Defaults to the 'pull' subcommand when none is specified."
        ),
        epilog=(
            "Examples:\n"
            f"  ruff-sync pull https://github.com/org/repo/blob/main/"
            f"{RuffConfigFileName.PYPROJECT_TOML}\n"
            f"  ruff-sync check https://github.com/org/repo/blob/main/"
            f"{RuffConfigFileName.PYPROJECT_TOML}\n"
            "  ruff-sync pull git@github.com:org/repo.git\n"
            "  ruff-sync pull ssh://git@gitlab.com/org/repo.git\n"
            "  ruff-sync check --semantic  # ignore formatting-only differences\n\n"
            f"The upstream URL can also be set in [tool.ruff-sync] in "
            f"{RuffConfigFileName.PYPROJECT_TOML}\n"
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
        nargs="*",
        help=f"One or more URLs to download the {RuffConfigFileName.PYPROJECT_TOML} file from."
        " Optional if defined in [tool.ruff-sync]. Upstreams are merged sequentially.",
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
        help=f"The parent path where {RuffConfigFileName.PYPROJECT_TOML} is located. Default: root",
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


PARSER: Final[ArgumentParser] = _get_cli_parser()


def _resolve_upstream(args: Any, config: Mapping[str, Any]) -> tuple[URL, ...]:
    """Resolve upstream URL(s) from CLI or config."""
    if args.upstream:
        return tuple(cast("Iterable[URL]", args.upstream))
    if "upstream" in config:
        config_upstream = config["upstream"]
        if isinstance(config_upstream, str):
            upstream = (URL(config_upstream),)
            LOGGER.info(f"📂 Using upstream from [tool.ruff-sync]: {upstream[0]}")
            return upstream
        if isinstance(config_upstream, list):
            upstreams = tuple(URL(u) for u in config_upstream)
            LOGGER.info(f"📂 Using {len(upstreams)} upstreams from [tool.ruff-sync]")
            return upstreams

        PARSER.error(
            "❌ upstream in [tool.ruff-sync] must be a string or a list of strings, "
            f"got {type(config_upstream).__name__}"
        )

    PARSER.error(
        "❌ the following arguments are required: upstream "
        f"(or define it in [tool.ruff-sync] in {RuffConfigFileName.PYPROJECT_TOML}) 💥"
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
) -> tuple[tuple[URL, ...], pathlib.Path, Iterable[str], str, str]:
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
    upstream = tuple(resolve_raw_url(u, branch=branch, path=path) for u in upstream)

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
