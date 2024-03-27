import pathlib
from collections.abc import Generator
from pprint import pformat as pf

import pytest
import respx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument

import ruff_sync


def test_ruff_sync():
    assert ruff_sync.__version__ == "0.0.1.dev0"


@pytest.fixture
def toml_s() -> str:
    """A sample pyproject.toml file with ruff config."""
    return """
    [tool.ruff.lint]
    target-version = "py38"
    line-length = 120
    lint.select = ["F", "ASYNC"]
    lint.ignore = ["W191", "E111"]

    [tool.ruff.lint.per-file-ignores]
    "__init__.py" = [
        "F401", # unused import
        "F403", # star imports
    ]
    """


@pytest.mark.parametrize(
    "exclude", [("per-file-ignores", "line-length"), ("ignore", "target-version"), ()]
)
def test_toml_ruff_parse(toml_s: str, exclude: tuple[str, ...]):
    original_toml_doc = tomlkit.parse(toml_s)
    orginal_keys = set(original_toml_doc["tool"]["ruff"]["lint"].keys())  # type: ignore[index,union-attr]
    print(f"{pf(orginal_keys)}")

    parsed_toml_doc = ruff_sync.toml_ruff_parse(toml_s, exclude=exclude)
    print(f"\n{pf(parsed_toml_doc, compact=True)}")

    lint_config: TOMLDocument = parsed_toml_doc["lint"]  # type: ignore[assignment]

    for section in exclude:
        assert section not in lint_config

    expected_sections = orginal_keys - set(exclude)
    for section in expected_sections:
        assert (
            section in original_toml_doc["tool"]["ruff"]["lint"]  # type: ignore[index,union-attr]
        ), f"{section} was not in original doc, fix test"

        assert section in lint_config, f"{section} was incorrectly excluded"


@pytest.fixture
def mock_http(toml_s: str) -> Generator[respx.MockRouter, None, None]:
    with respx.mock(base_url="https://example.com/") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=toml_s,
        )
        yield respx_mock


@pytest.mark.asyncio
async def test_sync(mock_http: respx.MockRouter):
    # TODO: mock file system
    upstream = URL("https://example.com/pyproject.toml")
    await ruff_sync.sync(ruff_sync.Arguments(upstream=upstream, source=pathlib.Path()))


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
