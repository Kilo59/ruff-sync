import asyncio
import pathlib
from argparse import ArgumentParser
from io import StringIO
from typing import Any, Final, NamedTuple

import httpx
from httpx import URL
from tomlkit import parse as toml_parse

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


def _parse_url(url: str) -> URL:
    return URL(url)


async def download(url: URL, client: httpx.AsyncClient) -> StringIO:
    """Download a file from a URL and return a StringIO object."""
    response = await client.get(url)
    response.raise_for_status()
    return StringIO(response.text)


async def main(args: Arguments) -> Any:
    print("Syncing Ruff...")
    async with httpx.AsyncClient() as client:
        file_buffer = await download(DEMO_URL, client)
        as_toml = toml_parse(file_buffer.read())
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
