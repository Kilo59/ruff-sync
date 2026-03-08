from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
import respx
from httpx import URL

import ruff_sync

if TYPE_CHECKING:
    from collections.abc import Generator

    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.fixture
def mock_http(toml_s: str) -> Generator[respx.MockRouter, None, None]:
    with respx.mock(base_url="https://example.com/", assert_all_called=False) as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=toml_s,
        )
        respx_mock.get("/ruff.toml").respond(
            200,
            content_type="text/plain",
            content='target-version = "py310"\nline-length = 99\n',
        )
        yield respx_mock


@pytest.fixture
def toml_s() -> str:
    """A sample pyproject.toml file with ruff config."""
    return """[tool.ruff]
target-version = "py38"
line-length = 120
[tool.ruff.lint]
select = ["F", "ASYNC"]
ignore = ["W191", "E111"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = [
    "F401", # unused import
    "F403", # star imports
]
"""


@pytest.mark.asyncio
async def test_pull_without_init_fails_on_missing_file(
    mock_http: respx.MockRouter, fs: FakeFilesystem, capsys: pytest.CaptureFixture[str]
):
    target_dir = pathlib.Path(fs.create_dir("empty_dir").path)  # type: ignore[arg-type]

    upstream = URL("https://example.com/pyproject.toml")
    result = await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=upstream,
            source=target_dir,
            exclude=(),
            verbose=0,
            init=False,
        )
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "Configuration file" in captured.out
    assert "does not exist" in captured.out
    assert "Pass the '--init' flag" in captured.out
    assert not (target_dir / "pyproject.toml").exists()


@pytest.mark.asyncio
async def test_pull_with_init_scaffolds_pyproject_toml(
    mock_http: respx.MockRouter, fs: FakeFilesystem
):
    """Test that pull scaffolds a pyproject.toml if --init is passed."""
    target_dir = pathlib.Path(fs.create_dir("empty_dir").path)  # type: ignore[arg-type]

    upstream = URL("https://example.com/pyproject.toml")
    result = await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=upstream,
            source=target_dir,
            exclude=(),
            verbose=0,
            init=True,
        )
    )

    assert result == 0
    scaffolded_file = target_dir / "pyproject.toml"
    assert scaffolded_file.exists()

    content = scaffolded_file.read_text()
    assert "[tool.ruff]" in content
    assert 'target-version = "py38"' in content


@pytest.mark.asyncio
async def test_pull_with_init_scaffolds_ruff_toml(mock_http: respx.MockRouter, fs: FakeFilesystem):
    """Test that pull scaffolds a ruff.toml if upstream is ruff.toml and --init is passed."""
    target_dir = pathlib.Path(fs.create_dir("empty_dir").path)  # type: ignore[arg-type]

    upstream = URL("https://example.com/ruff.toml")
    result = await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=upstream,
            source=target_dir,
            exclude=(),
            verbose=0,
            init=True,
        )
    )

    assert result == 0
    scaffolded_file = target_dir / "ruff.toml"
    assert scaffolded_file.exists()

    content = scaffolded_file.read_text()
    assert "[tool.ruff]" not in content
    assert 'target-version = "py310"' in content
    assert "line-length = 99" in content
