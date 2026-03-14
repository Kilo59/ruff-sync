from __future__ import annotations

import logging
import pathlib
import sys
from typing import TYPE_CHECKING

import pytest
import respx
from httpx import URL

import ruff_sync

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


def test_source_cli_deprecation(
    fs: FakeFilesystem,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    clear_ruff_sync_caches,
):
    """Test that --source CLI argument emits a deprecation warning and works as --to."""
    # Ensure we are in a clean directory
    test_dir = pathlib.Path("/app")
    fs.create_dir(str(test_dir))
    monkeypatch.chdir(str(test_dir))

    fs.create_file(str(test_dir / "pyproject.toml"), contents="[tool.ruff]\n")
    source_path = test_dir / "pyproject.toml"
    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, text="[tool.ruff]\ntarget-version = 'py310'\n"
        )

        monkeypatch.setattr(sys, "argv", ["ruff-sync", "pull", str(upstream_url), "--source", "."])
        with caplog.at_level(logging.WARNING, logger="ruff_sync"):
            exit_code = ruff_sync.main()
            assert exit_code == 0
            assert "--source is deprecated" in caplog.text

    assert "target-version = 'py310'" in source_path.read_text()


def test_source_config_deprecation(
    fs: FakeFilesystem,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    clear_ruff_sync_caches,
):
    """Test that source in [tool.ruff-sync] emits a deprecation warning."""
    test_dir = pathlib.Path("/app")
    fs.create_dir(str(test_dir))
    monkeypatch.chdir(str(test_dir))

    pyproject_content = """
[tool.ruff-sync]
upstream = "https://example.com/pyproject.toml"
source = "."
"""
    fs.create_file(str(test_dir / "pyproject.toml"), contents=pyproject_content)

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, text="[tool.ruff]\ntarget-version = 'py310'\n"
        )

        monkeypatch.setattr(sys, "argv", ["ruff-sync", "pull"])
        with caplog.at_level(logging.WARNING, logger="ruff_sync"):
            exit_code = ruff_sync.main()
            assert exit_code == 0
            assert "'source' is deprecated" in caplog.text

    assert "target-version = 'py310'" in (test_dir / "pyproject.toml").read_text()


@pytest.mark.parametrize(
    ["files", "upstream_url", "expected_target"],
    [
        ([], "https://ex.com/pyproject.toml", "pyproject.toml"),
        (["pyproject.toml"], "https://ex.com/ruff.toml", "pyproject.toml"),
        (["pyproject.toml", "ruff.toml"], "https://ex.com/pyproject.toml", "ruff.toml"),
        ([".ruff.toml"], "https://ex.com/pyproject.toml", ".ruff.toml"),
        ([], "https://ex.com/ruff.toml", "ruff.toml"),
    ],
)
def test_resolve_target_path_logic(
    fs: FakeFilesystem, files, upstream_url, expected_target, clear_ruff_sync_caches
):
    """Test the refined target path resolution logic."""
    target_dir = pathlib.Path("/test_dir")
    fs.create_dir(str(target_dir))
    for f in files:
        fs.create_file(str(target_dir / f))

    resolved = ruff_sync._resolve_target_path(target_dir, upstream_url)
    assert resolved == target_dir / expected_target
