from __future__ import annotations

import asyncio
import logging
import pathlib
import warnings
from argparse import ArgumentParser
from functools import lru_cache
from io import StringIO
from pprint import pformat as pf
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, overload

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, table
from tomlkit import key as toml_key
from tomlkit.container import OutOfOrderTableProxy
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__version__ = "0.0.1.dev0"

_DEFAULT_EXCLUDE: Final[set[str]] = {"per-file-ignores"}

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
    # TODO: determine if args was provided by user or not
    # https://docs.python.org/3/library/argparse.html#nargs
    parser = ArgumentParser()
    parser.add_argument(
        "--upstream",
        type=URL,
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
        type=set,
        default=_DEFAULT_EXCLUDE,
    )
    return parser


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
    toml: str | TOMLDocument, create_if_missing: bool = True, exclude: Iterable[str] = ()
) -> Table | None:
    """
    Get the tool.ruff section from a TOML string.
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
        LOGGER.info("No `tool.ruff` section found, creating it.")
        tool = table(True)
        ruff = table()
        tool.append("ruff", ruff)
        doc.append("tool", tool)
    if not isinstance(ruff, Table):
        raise TypeError(f"Expected table, got {type(ruff)}")
    for section in exclude:
        if section in ruff:
            LOGGER.info(f"Exluding section `lint.{section}` from ruff config.")
            ruff.pop(section)
    return ruff


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
    """
    Merge the source and upstream tool ruff config
    """
    source_tool_ruff = get_ruff_tool_table(source)
    if upstream_ruff_doc:
        source_tool_ruff.update(upstream_ruff_doc)  # type: ignore[index,union-attr]
        out_of_order: dict[str, OutOfOrderTableProxy] = {}

        # TODO: simplify this

        # fix out of order tables
        for key, value in upstream_ruff_doc.items():
            dotted_components = key.split(".")
            if len(dotted_components) > 1:
                LOGGER.info(f"Found dot-noted key: {key}")
            if isinstance(value, OutOfOrderTableProxy):
                out_of_order[key] = value
                LOGGER.debug(f"Found out of order table: {key}")
                for nested_key, nested_value in value.items():
                    dotted_key = toml_key([key, nested_key])
                    LOGGER.debug(f"Nested: {dotted_key} - {type(nested_value)}")
                    if isinstance(nested_value, Table):
                        LOGGER.debug(f"Nested {dotted_key} {type(nested_value).__name__}")
        LOGGER.debug(f"Out of order tables:\n{list(out_of_order.keys())}")
        LOGGER.debug(f"Out of order:\n{pf(list(out_of_order.values()))}")
        # remove out of order tables
        for key in out_of_order:
            LOGGER.debug(f"Removing out of order table: {key}")
            popped: OutOfOrderTableProxy = source_tool_ruff.pop(key)
            # now breakup the table and add it back in the correct order
            for nested_key, nested_value in popped.items():
                dotted_key = toml_key([key, nested_key])
                LOGGER.debug(f"Adding back: {dotted_key}")
                # TODO: isinstance check rather than try/except
                try:
                    source_tool_ruff[dotted_key] = nested_value
                except TOMLKitError as e:
                    LOGGER.debug(f"Error adding {dotted_key}: {e}")
                    table = {k: v for k, v in popped.items() if k == nested_key}
                    LOGGER.info(f"Adding Table: {pf(table)}")
                    source_tool_ruff.append(key, table)
    else:
        LOGGER.warning("No upstream ruff config section found.")
    return source


async def sync(
    args: Arguments,
) -> None:
    """Sync the upstream pyproject.toml file to the source directory."""
    print("Syncing Ruff...")
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
    print(f"Updated {_source_toml_path.relative_to(pathlib.Path.cwd())}")


PARSER: Final[ArgumentParser] = _get_cli_parser()


def main() -> None:
    args = PARSER.parse_args()
    # config = get_config(args.source)
    asyncio.run(
        sync(
            Arguments(
                upstream=args.upstream,
                source=args.source,
                exclude=args.exclude,
            )
        )
    )


if __name__ == "__main__":
    main()
