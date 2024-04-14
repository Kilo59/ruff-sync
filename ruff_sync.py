from __future__ import annotations

import asyncio
import logging
import pathlib
import warnings
from argparse import ArgumentParser
from functools import lru_cache
from io import StringIO
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, Final, Literal, NamedTuple

import httpx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument, nl
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

    if args.exclude:
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
    simple_updates: dict[str | Key, Any] = {}
    for section, value in upsteam_ruff.items():
        LOGGER.info(f"{section}: {type(value)}{value}")
        if not isinstance(value, (Table, OutOfOrderTableProxy)):
            simple_updates[section] = value
        else:
            for sub_section, sub_value in value.items():
                LOGGER.info(f"{section}.{sub_section}: {type(sub_value)}{sub_value}")
                if isinstance(sub_value, Table):
                    source_ruff.append(section, {sub_section: sub_value})
                    # newline after table
                    source_ruff.add(nl())
                else:
                    source_ruff[section][sub_section] = sub_value

    LOGGER.info(f"Update: ->\n{pf(simple_updates)}")
    source_ruff.update(simple_updates)
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
