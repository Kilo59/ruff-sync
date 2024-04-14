from __future__ import annotations

import asyncio
import logging
import pathlib
import warnings
from argparse import ArgumentParser
from functools import lru_cache
from io import StringIO
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple, overload

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, table
from tomlkit import key as toml_key
from tomlkit.container import OutOfOrderTableProxy
from tomlkit.items import Key, Table
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


# NOTE: this is not used
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
        "upstream",
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
        help=f"Exclude certain ruff.lint configs. Default: {' '.join(_DEFAULT_EXCLUDE)}",
        type=set,
        default=_DEFAULT_EXCLUDE,
    )
    return parser


def github_url_to_raw_url(url: URL) -> URL:
    """
    Convert a GitHub URL to its corresponding raw content URL

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


def filter_extra_items(
    toml: str | TOMLDocument, lint_exclude: Iterable[str] | None = None
) -> TOMLDocument:
    """
    Filter out all but the ruff section from a TOML document or string.
    If provided also exclude certain ruff configs.
    """
    if isinstance(toml, str):
        doc: TOMLDocument = tomlkit.parse(toml)
    else:
        doc = toml
    filtered_doc = TOMLDocument()
    ruff: Table | None = doc.get("tool", {}).get("ruff")
    if not ruff:
        LOGGER.warning("No `tool.ruff` section found.")
        return filtered_doc

    if lint_exclude:
        ruff_lint = ruff.get("lint")
        if not ruff_lint:
            raise KeyError(
                f"No `lint` section found in `tool.ruff`, cannot exclude {lint_exclude}"
            )
        for section in lint_exclude:
            LOGGER.info(f"Excluding section `lint.{section}` from ruff config.")
            ruff_lint.pop(section, None)

    tool = table(is_super_table=True)
    tool.append("ruff", ruff)
    filtered_doc.append("tool", tool)
    return filtered_doc


def toml_ruff_parse(toml_s: str, exclude: Iterable[str]) -> TOMLDocument:
    """Parse a TOML string for the tool.ruff section excluding certain ruff configs."""
    ruff_toml: TOMLDocument = tomlkit.parse(toml_s)["tool"]["ruff"]  # type: ignore[index,assignment]
    for section in exclude:
        LOGGER.info(f"Exluding section `lint.{section}` from ruff config.")
        ruff_toml["lint"].pop(section, None)  # type: ignore[union-attr]
    return ruff_toml


def _dotted_key_merge(source: Table, upstream: Table) -> Table:
    """
    Merge two tables with dotted keys.
    """
    to_update = source.copy()
    dotted_key_update: dict[Key, Any] = {}
    for key, value in upstream.items():
        # print(f"--{type(key)}{key} - {type(value)}{value}")
        if isinstance(value, OutOfOrderTableProxy):
            for sub_key, sub_value in value.items():
                dotted_key = toml_key([key, sub_key])
                print(f"  {dotted_key} - {type(sub_value)}{sub_value}")
                if isinstance(sub_value, Table):
                    print("    table")
                    to_update[key][sub_key] = sub_value
                else:
                    x = to_update.get(key, {})
                    y = x.get(sub_key)
                    print(f"{type(x)}{x=}")
                    print(f"{type(y)}{y=}")
                dotted_key_update[dotted_key] = sub_value
        # else:
        #     to_update[key] = value
    print(f"\n  dotted_key_update:\n{pf(dotted_key_update)}\n")
    print(f"{to_update.display_name}")
    if lint_select := dotted_key_update.get(toml_key(["lint", "select"])):
        print(f"  update {lint_select=}")
        to_update["lint"]["select"] = lint_select
    if lint_ingore := dotted_key_update.get(toml_key(["lint", "ignore"])):
        print(f"  update {lint_ingore=}")
        to_update["lint"]["ignore"] = lint_ingore

        # merged.append(dotted_key, value)
    # merged[dotted_key] = value
    # TODO: return {"tool.ruff": ..., "tool.ruff.lint.per-file_ignore": ...}
    # merged.update(update)
    return to_update


def merge_ruff_toml(
    source: TOMLDocument, filtered_upstream_doc: TOMLDocument
) -> TOMLDocument:
    """
    Merge the source and upstream tool ruff config
    """
    upstream_tool: Table | None = filtered_upstream_doc.get("tool")
    if upstream_tool:
        source_tool: Table = source["tool"]  # type: ignore[assignment]
        source_ruff = source_tool["ruff"]
        upstream_ruff = upstream_tool["ruff"]
        # add back any missing sections
        merged_ruff: Table = _dotted_key_merge(source_ruff, upstream_ruff)
        upstream_tool["ruff"] = merged_ruff
        source_tool.update(upstream_tool)
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
    # print(_source_toml_path.read_text())
    print("Exluding:", args.exclude)

    # NOTE: there's no particular reason to use async here.
    async with httpx.AsyncClient() as client:
        file_buffer = await download(args.upstream, client)
        LOGGER.info(f"Downloaded upstream file from {args.upstream}")

    upstream_doc: TOMLDocument = tomlkit.parse(file_buffer.getvalue())
    upsteam_ruff: Table | None = upstream_doc.get("tool", {}).get("ruff")
    if not upsteam_ruff:
        raise ValueError("No `tool.ruff` section found in upstream file.")

    source_doc: TOMLDocument = source_toml_file.read()
    source_tool: Table = source_doc["tool"]  # type: ignore[assignment]
    source_ruff: Table = source_tool["ruff"]  # type: ignore[assignment]

    # iterate over the upstream ruff config and update the corresponding section in the
    # source ruff config unless it is in the exclude list
    for section, value in upsteam_ruff.items():
        LOGGER.info(f"{section}: {type(value)}{value}")
        if not isinstance(value, (Table, OutOfOrderTableProxy)):
            source_ruff[section] = value
        else:
            LOGGER.warning(f"Handle {type(value)}")

    source_toml_file.write(source_doc)
    print(f"Updated {_source_toml_path.relative_to(pathlib.Path.cwd())}")


PARSER: Final[ArgumentParser] = _get_cli_parser()


def main() -> None:
    args = PARSER.parse_args()
    # config = get_config(args.source)

    # Convert non-raw github upstream url to the raw equivalent
    args.upstream = github_url_to_raw_url(args.upstream)

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
