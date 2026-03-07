from __future__ import annotations

import asyncio
import logging
import pathlib
import warnings
from argparse import ArgumentParser
from collections.abc import Iterable, Mapping
from functools import lru_cache
from io import StringIO
from typing import Any, Final, Literal, NamedTuple, overload

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, table
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile

__version__ = "0.0.1.dev3"

_DEFAULT_EXCLUDE: Final[set[str]] = {"lint.per-file-ignores"}

LOGGER = logging.getLogger(__name__)


class Arguments(NamedTuple):
    upstream: URL
    source: pathlib.Path
    exclude: Iterable[str]

    @classmethod
    @lru_cache(maxsize=1)
    def fields(cls) -> set[str]:
        return set(cls._fields)


@lru_cache(maxsize=1)
def get_config(
    source: pathlib.Path,
) -> Mapping[Literal["upstream", "source", "exclude"], str | list[str]]:
    local_toml = source / "pyproject.toml"
    # TODO: use pydantic to validate the toml file
    cfg_result = {}
    if local_toml.exists():
        toml = tomlkit.parse(local_toml.read_text())
        config = toml.get("tool", {}).get("ruff-sync")
        if config:
            for arg, value in config.items():
                if arg in Arguments.fields():
                    cfg_result[arg] = value
                else:
                    warnings.warn(f"Unknown ruff-sync configuration: {arg}", stacklevel=2)
    return cfg_result


@lru_cache(maxsize=1)
def _resolve_source(source: str | pathlib.Path) -> pathlib.Path:
    if isinstance(source, str):
        source = pathlib.Path(source)
    return source.resolve(strict=True)


def _get_cli_parser() -> ArgumentParser:
    # https://docs.python.org/3/library/argparse.html#nargs
    parser = ArgumentParser()
    parser.add_argument(
        "upstream",
        type=URL,
        nargs="?",
        help="The URL to download the pyproject.toml file from.",
    )
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        default=".",
        help="The directory to sync the pyproject.toml file to. Default: .",
        required=False,
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help=f"Exclude certain ruff configs. Default: {' '.join(_DEFAULT_EXCLUDE)}",
        default=None,
    )
    return parser


def github_url_to_raw_url(url: URL) -> URL:
    """Convert a GitHub URL to its corresponding raw content URL

    Args:
        url (URL): The GitHub URL to be converted.

    Returns:
        URL: The corresponding raw content URL.
    """
    url_str = str(url)
    if "github.com" in url_str and "/blob/" in url_str:
        raw_url_str = url_str.replace("github.com", "raw.githubusercontent.com").replace(
            "/blob/", "/"
        )
        return httpx.URL(raw_url_str)
    else:
        return url


async def download(url: URL, client: httpx.AsyncClient) -> StringIO:
    """Download a file from a URL and return a StringIO object."""
    response = await client.get(url)
    response.raise_for_status()
    return StringIO(response.text)


@overload
def get_ruff_tool_table(
    toml: str | TOMLDocument,
    create_if_missing: Literal[True] = ...,
    exclude: Iterable[str] = ...,
) -> Table: ...


@overload
def get_ruff_tool_table(
    toml: str | TOMLDocument,
    create_if_missing: Literal[False] = ...,
    exclude: Iterable[str] = ...,
) -> Table | None: ...


def get_ruff_tool_table(
    toml: str | TOMLDocument,
    create_if_missing: bool = True,
    exclude: Iterable[str] = (),
) -> Table | None:
    """Get the tool.ruff section from a TOML string.
    If it does not exist, create it.
    """
    if isinstance(toml, str):
        doc: TOMLDocument = tomlkit.parse(toml)
    else:
        doc = toml
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
        raise TypeError(f"Expected table, got {type(ruff)}")
    _apply_exclusions(ruff, exclude)
    return ruff


def _apply_exclusions(tbl: Table, exclude: Iterable[str]) -> None:
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
        LOGGER.info(f"Exluding section `lint.{section}` from ruff config.")
        ruff_toml["lint"].pop(section, None)  # type: ignore[union-attr]
    return ruff_toml


def merge_ruff_toml(
    source: TOMLDocument, upstream_ruff_doc: TOMLDocument | Table | None
) -> TOMLDocument:
    """Merge the source and upstream tool ruff config with better whitespace preservation."""  # noqa: E501
    if not upstream_ruff_doc:
        LOGGER.warning("No upstream ruff config section found.")
        return source

    source_tool_ruff = get_ruff_tool_table(source)

    def _recursive_update(source_table: Any, upstream: Any) -> None:
        """Recursively update a TOML table to preserve formatting of existing keys."""
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
                    # Overwrite existing value
                    source_table[key] = (
                        value.unwrap() if hasattr(value, "unwrap") else value
                    )
            else:
                # Add new key/value
                source_table[key] = value.unwrap() if hasattr(value, "unwrap") else value

    _recursive_update(source_tool_ruff, upstream_ruff_doc)

    return source


async def sync(
    args: Arguments,
) -> None:
    """Sync the upstream pyproject.toml file to the source directory."""
    print("🔄 Syncing Ruff...")
    if args.source.is_file():
        _source_toml_path = args.source
    else:
        _source_toml_path = args.source / "pyproject.toml"
    source_toml_file = TOMLFile(_source_toml_path.resolve(strict=True))

    # NOTE: there's no particular reason to use async here.
    async with httpx.AsyncClient() as client:
        file_buffer = await download(args.upstream, client)
        LOGGER.info(f"Downloaded upstream file from {args.upstream}")

    upstream_ruff_toml = get_ruff_tool_table(
        file_buffer.read(), create_if_missing=False, exclude=args.exclude
    )
    merged_toml = merge_ruff_toml(
        source_toml_file.read(),
        upstream_ruff_toml,
    )
    source_toml_file.write(merged_toml)
    print(f"✅ Updated {_source_toml_path.resolve().relative_to(pathlib.Path.cwd())}")


PARSER: Final[ArgumentParser] = _get_cli_parser()


def main() -> None:
    args = PARSER.parse_args()
    config = get_config(args.source)

    # Resolve upstream: use CLI value if explicitly provided, else file config
    upstream: URL
    if args.upstream:
        upstream = args.upstream
    elif "upstream" in config:
        # get_config returns str | list[str]
        upstream = URL(config["upstream"])  # type: ignore[arg-type]
        LOGGER.info(f"📂 Using upstream from [tool.ruff-sync]: {upstream}")
    else:
        PARSER.error(
            "❌ the following arguments are required: upstream "
            "(or define it in [tool.ruff-sync] in pyproject.toml) 💥"
        )

    # Merge exclude: use CLI value if explicitly provided, else file config,
    # else the built-in default.
    exclude: Iterable[str]
    if args.exclude is not None:
        # User passed --exclude on the CLI — that takes precedence
        exclude = args.exclude
    elif "exclude" in config:
        exclude = config["exclude"]
        LOGGER.info(f"🚫 Using exclude from [tool.ruff-sync]: {list(exclude)}")
    else:
        exclude = _DEFAULT_EXCLUDE

    # Convert non-raw github upstream url to the raw equivalent
    upstream = github_url_to_raw_url(upstream)

    asyncio.run(
        sync(
            Arguments(
                upstream=upstream,
                source=args.source,
                exclude=exclude,
            )
        )
    )


if __name__ == "__main__":
    main()
