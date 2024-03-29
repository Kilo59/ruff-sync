from __future__ import annotations

import asyncio
import pathlib
import warnings
from argparse import ArgumentParser
from functools import lru_cache
from io import StringIO
from typing import TYPE_CHECKING, Final, Literal, NamedTuple

import httpx
import tomlkit
from httpx import URL

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

__version__ = "0.0.1.dev0"

_DEFAULT_EXCLUDE: Final[set[str]] = {"per-file-ignores"}


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
                    warnings.warn(
                        f"Unknown ruff-sync configuration: {arg}", stacklevel=2
                    )
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


def toml_ruff_parse(toml_s: str, exclude: Iterable[str]) -> tomlkit.TOMLDocument:
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


async def sync(
    args: Arguments,
) -> None:
    """Sync the upstream pyproject.toml file to the source directory."""
    print("Syncing Ruff...")
    if args.source.is_file():
        source_toml_path = args.source
    else:
        source_toml_path = args.source / "pyproject.toml"
    source_toml_path = source_toml_path.resolve(strict=True)

    # NOTE: there's no particular reason to use async here.
    async with httpx.AsyncClient() as client:
        file_buffer = await download(args.upstream, client)

    ruff_toml = toml_ruff_parse(file_buffer.read(), exclude=args.exclude)
    merged_toml = merge_ruff_toml(
        tomlkit.parse(source_toml_path.read_text()),
        ruff_toml,
    )
    source_toml_path.write_text(merged_toml.as_string())
    print(f"Updated {source_toml_path.relative_to(pathlib.Path.cwd())}")


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
