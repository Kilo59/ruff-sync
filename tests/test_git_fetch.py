from __future__ import annotations

import pathlib
import subprocess
from unittest.mock import MagicMock, patch  # noqa: TID251

import pytest
from httpx import URL, AsyncClient

from ruff_sync import fetch_upstream_config, resolve_raw_url


@pytest.mark.asyncio
async def test_fetch_upstream_config_git():
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:
        # Mock what git clone does by writing to the temp directory
        def side_effect(cmd, **_kwargs):
            # cmd is like: ['git', 'clone', '--depth', '1', '--branch', 'main', '...', '/tmp/...']
            # cmd[-1] is the temp_dir
            temp_dir = pathlib.Path(cmd[-1])
            (temp_dir / "pyproject.toml").write_text("[tool.ruff]\nselect = ['E']")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        async with AsyncClient() as client:
            result = await fetch_upstream_config(url, client, branch="main", path="")

        assert result.read() == "[tool.ruff]\nselect = ['E']"

        # Verify the subprocess arguments
        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        # The last argument is the auto-generated temp_dir path
        assert args[0][:-1] == [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "main",
            "git@github.com:Kilo59/ruff-sync.git",
        ]
        assert _kwargs["check"] is True


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_with_path():
    url = URL("ssh://git@github.com/Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:

        def side_effect(cmd, **_kwargs):
            temp_dir = pathlib.Path(cmd[-1])
            target_path = temp_dir / "sub" / "dir"
            target_path.mkdir(parents=True)
            (target_path / "pyproject.toml").write_text("[tool.ruff]\nselect = ['F']")
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        async with AsyncClient() as client:
            result = await fetch_upstream_config(url, client, branch="main", path="sub/dir")

        assert result.read() == "[tool.ruff]\nselect = ['F']"

        mock_run.assert_called_once()
        args, _kwargs = mock_run.call_args
        assert args[0][:-1] == [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "main",
            "ssh://git@github.com/Kilo59/ruff-sync.git",
        ]


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_failure():
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="Repository not found"
        )

        with pytest.raises(subprocess.CalledProcessError):
            async with AsyncClient() as client:
                await fetch_upstream_config(url, client, branch="main", path="")


def test_resolve_raw_url_git_ssh():
    url = URL("git@github.com:Kilo59/ruff-sync.git")
    resolved = resolve_raw_url(url)
    assert resolved == url

    url2 = URL("ssh://git@github.com/Kilo59/ruff-sync.git")
    resolved2 = resolve_raw_url(url2)
    assert resolved2 == url2

    url3 = URL("git+ssh://git@github.com/Kilo59/ruff-sync.git")
    resolved3 = resolve_raw_url(url3)
    assert resolved3 == url3
