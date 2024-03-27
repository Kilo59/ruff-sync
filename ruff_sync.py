import asyncio
import pathlib
from argparse import ArgumentParser
from collections.abc import Iterable
from io import StringIO
from typing import Any, Final, NamedTuple

import httpx
import tomlkit
from httpx import URL

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


async def main(args: Arguments) -> Any:
    print("Syncing Ruff...")
    async with httpx.AsyncClient() as client:
        file_buffer = await download(DEMO_URL, client)
        as_toml = toml_ruff_parse(file_buffer.read())
        print(as_toml)


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
