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


@pytest.mark.asyncio
async def test_pull_init_uses_existing_pyproject_toml(
    mock_http: respx.MockRouter, fs: FakeFilesystem, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: existing pyproject.toml, no ruff.toml or .ruff.toml
    directory = fs.create_dir("project_with_pyproject")
    target_dir = pathlib.Path(directory.path)  # type: ignore[arg-type]
    pyproject_path = target_dir / "pyproject.toml"

    fs.create_file(str(pyproject_path), contents="[tool.ruff]\nline-length = 79\n")

    upstream = URL("https://example.com/pyproject.toml")
    mock_http.get(str(upstream)).respond(200, text="[tool.ruff]\nline-length = 88\n")

    # Act
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

    # Assert: command succeeded, existing pyproject.toml was used as target
    assert result == 0
    captured = capsys.readouterr()
    assert "pyproject.toml" in captured.out

    assert pyproject_path.exists()
    assert (target_dir / "ruff.toml").exists() is False
    assert (target_dir / ".ruff.toml").exists() is False

    contents = pyproject_path.read_text()
    assert "line-length = 88" in contents


@pytest.mark.asyncio
async def test_pull_prefers_dot_ruff_toml_over_pyproject_toml(
    mock_http: respx.MockRouter, fs: FakeFilesystem, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: both pyproject.toml and .ruff.toml exist
    directory = fs.create_dir("project_with_pyproject_and_dot_ruff")
    target_dir = pathlib.Path(directory.path)  # type: ignore[arg-type]
    pyproject_path = target_dir / "pyproject.toml"
    dot_ruff_path = target_dir / ".ruff.toml"

    fs.create_file(str(pyproject_path), contents="[tool.ruff]\nline-length = 79\n")
    fs.create_file(str(dot_ruff_path), contents='target-version = "py310"\nline-length = 100\n')

    upstream = URL("https://example.com/ruff.toml")
    mock_http.get(str(upstream)).respond(200, text='target-version = "py310"\nline-length = 88\n')

    # Act: no --init, should update existing config, preferring .ruff.toml
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

    # Assert: command succeeded and .ruff.toml was selected and updated
    assert result == 0
    captured = capsys.readouterr()
    assert ".ruff.toml" in captured.out

    assert pyproject_path.exists()
    assert dot_ruff_path.exists()

    pyproject_contents = pyproject_path.read_text()
    dot_ruff_contents = dot_ruff_path.read_text()

    # pyproject.toml should remain unchanged
    assert "line-length = 79" in pyproject_contents
    # .ruff.toml should be updated with the upstream contents
    assert "line-length = 88" in dot_ruff_contents


@pytest.mark.asyncio
async def test_pull_updates_existing_dot_ruff_toml(
    mock_http: respx.MockRouter, fs: FakeFilesystem, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: only .ruff.toml exists
    directory = fs.create_dir("project_with_dot_ruff_only")
    target_dir = pathlib.Path(directory.path)  # type: ignore[arg-type]
    dot_ruff_path = target_dir / ".ruff.toml"

    fs.create_file(str(dot_ruff_path), contents='target-version = "py310"\nline-length = 79\n')

    upstream = URL("https://example.com/ruff.toml")
    mock_http.get(str(upstream)).respond(200, text='target-version = "py310"\nline-length = 120\n')

    # Act
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

    # Assert: command succeeded, .ruff.toml was updated, and no new files created
    assert result == 0
    captured = capsys.readouterr()
    assert ".ruff.toml" in captured.out

    assert dot_ruff_path.exists()
    assert (target_dir / "ruff.toml").exists() is False
    assert (target_dir / "pyproject.toml").exists() is False

    contents = dot_ruff_path.read_text()
    assert "line-length = 120" in contents


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
