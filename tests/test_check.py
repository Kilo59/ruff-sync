from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
import respx
from httpx import URL

import ruff_sync

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.asyncio
async def test_check_in_sync(fs: FakeFilesystem):
    # Setup
    pyproject_content = """
[tool.ruff]
target-version = "py310"

"""
    fs.create_file("pyproject.toml", contents=pyproject_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=pyproject_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 0


@pytest.mark.asyncio
async def test_check_out_of_sync(fs: FakeFilesystem, capsys):
    # Setup
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.out
        assert '-target-version = "py310"' in captured.out
        assert '+target-version = "py311"' in captured.out


@pytest.mark.asyncio
async def test_check_semantic_sync(fs: FakeFilesystem):
    # Setup - only whitespace/comments differ
    local_content = """
[tool.ruff]
# Some comment
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py310"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        # Strict check should fail
        args_strict = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
        assert await ruff_sync.check(args_strict) == 1

        # Semantic check should pass
        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 0


@pytest.mark.asyncio
async def test_check_semantic_out_of_sync(fs: FakeFilesystem):
    # Setup - actual values differ
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 1


@pytest.mark.asyncio
async def test_check_semantic_diff_output(fs: FakeFilesystem, capsys):
    # Setup - actual values differ
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=upstream_url,
            source=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.out
        assert "--- local (semantic)" in captured.out
        assert "+++ upstream (semantic)" in captured.out
        # Check for JSON-style diff content
        assert '-  "target-version": "py310"' in captured.out
        assert '+  "target-version": "py311"' in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
