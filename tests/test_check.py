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
            upstream=(upstream_url,),
            to=source_path,
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
            upstream=(upstream_url,),
            to=source_path,
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
async def test_check_pre_commit_out_of_sync(fs: FakeFilesystem, caplog):
    # Setup
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    # Mock uv.lock and .pre-commit-config.yaml to be out of sync
    fs.create_file("uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.0
    hooks:
      - id: ruff
"""
    fs.create_file(".pre-commit-config.yaml", contents=config_content)

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=local_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            pre_commit=True,
        )

        # Ruff config matches completely, but pre_commit is out of sync -> Exit code 2
        exit_code = await ruff_sync.check(args)
        assert exit_code == 2

        assert "pre-commit ruff hook is out of sync" in caplog.text


@pytest.mark.asyncio
async def test_check_semantic_sync(fs: FakeFilesystem):
    # A local comment does NOT make you out of sync — ruff-sync only adds/updates
    # keys, it never strips local-only additions like comments.
    local_content = """
[tool.ruff]
# Some local comment
target-version = "py310"
line-length = 90
"""
    upstream_content = """
[tool.ruff]
target-version = "py310"
line-length = 90
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

        # Strict check: merging upstream produces no text change → in sync
        args_strict = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
        assert await ruff_sync.check(args_strict) == 0

        # Semantic check also passes — values are identical
        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
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
            upstream=(upstream_url,),
            to=source_path,
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
            upstream=(upstream_url,),
            to=source_path,
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


@pytest.mark.asyncio
async def test_check_multi_upstream(fs: FakeFilesystem, capsys):
    """Check supports multiple upstreams and bases status on the fully merged result."""
    # Setup
    local_content = """
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F"]
"""
    upstream1_content = """
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E"]
"""
    upstream2_content = """
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F"]
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    u1_url = URL("https://example.com/u1/pyproject.toml")
    u2_url = URL("https://example.com/u2/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/u1/pyproject.toml").respond(200, content=upstream1_content)
        respx_mock.get("/u2/pyproject.toml").respond(200, content=upstream2_content)

        args = ruff_sync.Arguments(
            command="check",
            upstream=(u1_url, u2_url),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        # 1. Fully merged config matches local -> success
        assert await ruff_sync.check(args) == 0

        # 2. Local config deviates from the *merged* result -> failure
        # (e.g. local matches only upstream1, but upstream2 should have overridden it)
        source_path.write_text(upstream1_content)
        assert await ruff_sync.check(args) == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.out
        assert "+line-length = 100" in captured.out
        assert '+select = ["E", "F"]' in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
