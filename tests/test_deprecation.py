from __future__ import annotations

import logging
import pathlib
import sys
from typing import TYPE_CHECKING

import pytest
import respx
from httpx import URL

import ruff_sync
import ruff_sync.cli

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
    """Test that source in [tool.ruff-sync] emits a deprecation warning
    and that `to` takes precedence.
    """
    test_dir = pathlib.Path("/app")
    fs.create_dir(str(test_dir))
    monkeypatch.chdir(str(test_dir))

    # Case 1: Only `source` is set, verify deprecation warning.
    pyproject = test_dir / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
source = "src"
""".lstrip()
    )

    with caplog.at_level(logging.WARNING, logger="ruff_sync"):
        # get_config should still work, but emit a deprecation warning for `source`.
        config = ruff_sync.get_config(test_dir)
    assert "'source' is deprecated" in caplog.text

    # `source` should be mapped to `to` when `to` is not set.
    assert config["to"] == "src"

    caplog.clear()
    ruff_sync.get_config.cache_clear()

    # Case 2: Both `source` and `to` are set, verify `to` takes precedence.
    pyproject.write_text(
        """
[tool.ruff-sync]
source = "src-ignored"
to = "target-dir"
""".lstrip()
    )

    with caplog.at_level(logging.WARNING, logger="ruff_sync"):
        config_both = ruff_sync.get_config(test_dir)

    # Still warn about deprecation of `source`.
    assert "'source' is deprecated" in caplog.text

    # Crucially, `to` must determine the target path when both are present.
    assert config_both["to"] == "target-dir"

    caplog.clear()
    ruff_sync.get_config.cache_clear()

    # Case 3: Test that the final resolved path in Arguments uses config[to]
    # when CLI '--to' is not provided.
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://example.com/pyproject.toml"
to = "sub-project"
""".lstrip()
    )

    # Mock the upstream request
    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(200, text="[tool.ruff]\n")

        # No --to or --source on CLI, but use --init to allow creating the sub-project file
        monkeypatch.setattr(sys, "argv", ["ruff-sync", "pull", "--init"])

        # We need to make sure sub-project directory exists since main() will call
        # get_config(to_val). Wait, get_config(initial_to) finds the config in
        # the CWD (initial_to = Path())
        # Then _resolve_to(args, config, initial_to) returns initial_to / "sub-project".

        exit_code = ruff_sync.main()
        assert exit_code == 0

    # The file should have been created in sub-project/pyproject.toml
    # (assuming sub-project/ directory was created or handled by pull())
    assert (test_dir / "sub-project" / "pyproject.toml").exists()

    # Case 4: Test that 'to = "."' in config resolves relative to the config file
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://example.com/pyproject.toml"
to = "."
""".lstrip()
    )
    ruff_sync.get_config.cache_clear()
    monkeypatch.setattr(sys, "argv", ["ruff-sync", "pull"])

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(200, text="[tool.ruff]\n")
        exit_code = ruff_sync.main()
        assert exit_code == 0

    assert (test_dir / "pyproject.toml").exists()


@pytest.mark.parametrize(
    ["files", "upstream_url", "to_path", "expected_target_name"],
    [
        ([], "https://ex.com/pyproject.toml", "/test_dir", "pyproject.toml"),
        (["pyproject.toml"], "https://ex.com/ruff.toml", "/test_dir", "pyproject.toml"),
        (
            ["pyproject.toml", "ruff.toml"],
            "https://ex.com/pyproject.toml",
            "/test_dir",
            "ruff.toml",
        ),
        ([".ruff.toml"], "https://ex.com/pyproject.toml", "/test_dir", ".ruff.toml"),
        ([], "https://ex.com/ruff.toml", "/test_dir", "ruff.toml"),
        # Current directory cases
        ([], "https://ex.com/pyproject.toml", ".", "pyproject.toml"),
        (["ruff.toml"], "https://ex.com/pyproject.toml", ".", "ruff.toml"),
        ([], "https://ex.com/pyproject.toml", pathlib.Path(), "pyproject.toml"),
        # Direct file path cases
        (
            ["ruff.toml"],
            "https://ex.com/pyproject.toml",
            "/test_dir/ruff.toml",
            "ruff.toml",
        ),
        (
            ["pyproject.toml"],
            "https://ex.com/ruff.toml",
            "/test_dir/pyproject.toml",
            "pyproject.toml",
        ),
        # File path doesn't even need to exist if it's explicitly a file path
        ([], "https://ex.com/ruff.toml", "/test_dir/my-custom-ruff.toml", "my-custom-ruff.toml"),
    ],
)
def test_resolve_target_path_logic(  # noqa: PLR0913
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
    files,
    upstream_url,
    to_path,
    expected_target_name,
    clear_ruff_sync_caches,
):
    """Test the refined target path resolution logic."""
    target_dir = pathlib.Path("/test_dir")
    fs.create_dir(str(target_dir))
    for f in files:
        fs.create_file(str(target_dir / f))
    to = pathlib.Path(to_path)
    # For relative paths (like "."), we need to be in the target_dir for .exists() to work
    if not to.is_absolute():
        monkeypatch.chdir(str(target_dir))

    # If testing a direct file path that shouldn't exist yet, we don't always create it
    if not to.exists() and to.suffix == ".toml" and "/test_dir/" in str(to):
        if not to.parent.exists():
            fs.create_dir(str(to.parent))
        fs.create_file(str(to))

    resolved = ruff_sync.core.resolve_target_path(to, [upstream_url])
    assert resolved.name == expected_target_name
    if to.is_file():
        assert resolved == to
    else:
        assert resolved == to / expected_target_name
