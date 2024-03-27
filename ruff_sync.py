from __future__ import annotations

import asyncio
import pathlib
from argparse import ArgumentParser
from io import StringIO
from typing import TYPE_CHECKING, Any, Final, NamedTuple

import httpx
import tomlkit
from httpx import URL

if TYPE_CHECKING:
    from collections.abc import Iterable

DEMO_URL = URL("https://raw.githubusercontent.com/great-expectations/cloud/main/pyproject.toml")


def _get_cli_parser() -> ArgumentParser:
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
        help="The directory to sync the pyproject.toml file to.",
        required=False,
    )
    return parser


class Arguments(NamedTuple):
    upstream: URL
    source: pathlib.Path


async def download(url: URL, client: httpx.AsyncClient) -> StringIO:
    """Download a file from a URL and return a StringIO object."""
    response = await client.get(url)
    response.raise_for_status()
    return StringIO(response.text)


def toml_ruff_parse(
    toml_s: str, exclude: Iterable[str] = ("per-file-ignores",)
) -> tomlkit.TOMLDocument:
    """Parse a TOML string for the tool.ruff section excluding certain ruff configs."""
    ruff_toml: tomlkit.TOMLDocument = tomlkit.parse(toml_s)["tool"]["ruff"]  # type: ignore[index,assignment]
    for section in exclude:
        ruff_toml["lint"].pop(section, None)  # type: ignore[union-attr]
    return ruff_toml


def merge_ruff_toml(
    source: tomlkit.TOMLDocument, upstream_update: tomlkit.TOMLDocument
) -> tomlkit.TOMLDocument:
    """Merge the source and upstream ruff toml config."""
    source["tool"]["ruff"].update(upstream_update)  # type: ignore[index,union-attr]
    return source


async def main(args: Arguments) -> Any:
    print("Syncing Ruff...")
    if args.source.is_file():
        source_toml_path = args.source
    else:
        source_toml_path = args.source / "pyproject.toml"
    source_toml_path = source_toml_path.resolve(strict=True)

    async with httpx.AsyncClient() as client:
        file_buffer = await download(DEMO_URL, client)

    ruff_toml = toml_ruff_parse(file_buffer.read())
    merged_toml = merge_ruff_toml(
        tomlkit.parse(source_toml_path.read_text()),
        ruff_toml,
    )
    source_toml_path.write_text(merged_toml.as_string())
    print(f"Updated {source_toml_path.relative_to(pathlib.Path.cwd())}")


PARSER: Final[ArgumentParser] = _get_cli_parser()

if __name__ == "__main__":
    args = PARSER.parse_args()
    asyncio.run(
        main(
            Arguments(
                upstream=args.upstream,
                source=args.source,
            )
        )
    )
